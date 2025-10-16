# app.py

import time
import re
import csv
import os
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from flask import Flask, render_template, request, jsonify

# Importa utilitários do Google Sheets
ler_produtos_via_sheets_csv = None
ler_produtos_via_api = None
try:
    from google_sheets import ler_produtos_via_sheets_csv, ler_produtos_via_api
    print("✓ Módulo google_sheets carregado com sucesso")
    print(f"  - ler_produtos_via_sheets_csv: {ler_produtos_via_sheets_csv}")
    print(f"  - ler_produtos_via_api: {ler_produtos_via_api}")
except ImportError as e:
    print(f"⚠ google_sheets não encontrado: {e}")
except Exception as e:
    print(f"⚠ Erro ao importar google_sheets: {e}")
    import traceback
    traceback.print_exc()

# --- Configuração do Flask ---
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # Permite caracteres não-ASCII no JSON
app.config['JSON_SORT_KEYS'] = False  # Mantém ordem das chaves

# Cache para produtos (evita recarregar CSV toda vez)
_produtos_cache = None
_cache_timestamp = None

# --- FUNÇÃO PARA CARREGAR PRODUTOS DA PLANILHA ---
def carregar_produtos_planilha(force_reload=False, csv_filename: str | None = None):
    """
    Carrega os produtos da fonte configurada:
    - Google Sheets (CSV export ou API) se DATA_SOURCE estiver definido
    - Fallback: CSV local
    """
    global _produtos_cache, _cache_timestamp

    if not force_reload and _produtos_cache is not None:
        return _produtos_cache

    produtos = []

    # 1) Tenta Google Sheets conforme DATA_SOURCE
    data_source = (os.getenv('DATA_SOURCE') or '').strip().lower()
    try:
        if data_source == 'sheets_csv' and ler_produtos_via_sheets_csv:
            sheets_url = os.getenv('SHEETS_CSV_URL', '').strip()
            if sheets_url:
                print("→ Lendo produtos via Google Sheets (CSV export)...")
                produtos, meta = ler_produtos_via_sheets_csv(sheets_url)
                if produtos:
                    print(f"✓ Sheets CSV carregado. Total: {len(produtos)} | Delimitador: {meta.get('delimiter')}")
                    _produtos_cache = produtos
                    _cache_timestamp = time.time()
                    return produtos
                else:
                    print("⚠ Sheets CSV retornou vazio. Indo para fallback (CSV local).")
            else:
                print("⚠ SHEETS_CSV_URL não configurado. Indo para fallback (CSV local).")

        if data_source == 'sheets_api' and ler_produtos_via_api:
            sheets_id = os.getenv('SHEETS_ID', '').strip()
            sheets_tab_or_range = os.getenv('SHEETS_TAB', '').strip() or os.getenv('SHEETS_RANGE', '').strip()
            creds_path = os.getenv('SHEETS_CREDENTIALS_FILE', '').strip()
            if sheets_id and creds_path:
                print("→ Lendo produtos via Google Sheets API...")
                produtos, meta = ler_produtos_via_api(sheets_id, sheets_tab_or_range or None, creds_path)
                if produtos:
                    print(f"✓ Sheets API carregado. Total: {len(produtos)} | Worksheet: {meta.get('worksheet')}")
                    _produtos_cache = produtos
                    _cache_timestamp = time.time()
                    return produtos
                else:
                    print(f"⚠ Sheets API sem dados válidos. Headers: {meta.get('headers')} | Fallback (CSV local).")
            else:
                print("⚠ SHEETS_ID ou SHEETS_CREDENTIALS_FILE ausente. Fallback (CSV local).")
    except Exception as e:
        print(f"✗ Erro ao ler do Google Sheets ({data_source}): {e}. Fallback (CSV local).")

    # 2) Fallback para CSV local (com autodetecção)
    # Se já tem cache e não forçou reload, retorna do cache
    if not force_reload and _produtos_cache is not None:
        return _produtos_cache
    
    produtos = []
    
    # Permite sobrescrever via argumento ou variável de ambiente
    csv_candidates = []
    if csv_filename:
        csv_candidates.append(csv_filename)
    env_csv = os.getenv('PRODUTOS_CSV')
    if env_csv:
        csv_candidates.append(env_csv)
    # Ordem de preferência padrão
    csv_candidates.extend(['produtos.csv', 'produtos2.csv'])

    base_dir = os.path.dirname(__file__)
    csv_path = None
    for candidate in csv_candidates:
        candidate_path = candidate if os.path.isabs(candidate) else os.path.join(base_dir, candidate)
        if os.path.exists(candidate_path):
            csv_path = candidate_path
            break

    if not csv_path:
        print("✗ Nenhum arquivo de produtos encontrado.")
        print("  Procurei por: ", ', '.join(csv_candidates))
        return produtos
    
    # Lista de codificações para tentar
    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
    # Lista de delimitadores para tentar
    delimiters = [';', ',', '\t', '|']
    
    def _norm(s: str | None) -> str:
        if s is None:
            return ''
        # Remove BOM, espaços e normaliza para UPPER sem underscores diferentes
        return re.sub(r"\s+", '', str(s).replace('\ufeff', '').strip()).upper()

    expected = ['COD_PRODUTO', 'NOMEPRODUTOECOMM', 'COD_BARRAS', 'URLECOMMERCEIMG', 'PRODUCTURL']
    expected_norm = [_norm(x) for x in expected]
    # Aliases comuns para tolerar planilhas variantes
    aliases = {
        'CODPRODUTO': 'COD_PRODUTO',
        'SKU': 'COD_PRODUTO',
        'NOME': 'NOMEPRODUTOECOMM',
        'NOMEPRODUTO': 'NOMEPRODUTOECOMM',
        'NOME_PRODUTO': 'NOMEPRODUTOECOMM',
        'DESCRICAO': 'NOMEPRODUTOECOMM',
        'CODBARRAS': 'COD_BARRAS',
        'EAN': 'COD_BARRAS',
        'URLIMG': 'URLECOMMERCEIMG',
        'IMAGEM': 'URLECOMMERCEIMG',
        'URLIMAGEM': 'URLECOMMERCEIMG',
        'URL': 'PRODUCTURL',
        'LINK': 'PRODUCTURL',
        'PRODUCT_URL': 'PRODUCTURL',
        'URL_PRODUTO': 'PRODUCTURL'
    }

    last_detected_headers = None
    
    for encoding in encodings:
        for delimiter in delimiters:
            try:
                with open(csv_path, 'r', encoding=encoding, errors='replace', newline='') as file:
                    reader = csv.DictReader(file, delimiter=delimiter)
                    fieldnames = reader.fieldnames or []
                    detected_norm = [_norm(h) for h in fieldnames]
                    last_detected_headers = fieldnames[:]

                    # Monta um mapeamento de nome esperado -> nome real da planilha
                    mapping: dict[str, str] = {}
                    for idx, norm_name in enumerate(detected_norm):
                        real_name = fieldnames[idx]
                        # Se for exatamente um dos esperados
                        if norm_name in expected_norm:
                            i = expected_norm.index(norm_name)
                            mapping[expected[i]] = real_name
                        # Se for um alias, mapeia para o esperado correspondente
                        elif norm_name in aliases:
                            canonical = aliases[norm_name]
                            # Mapeia apenas se ainda não definido
                            mapping.setdefault(canonical, real_name)

                    # Verifica se conseguimos mapear todos os esperados
                    if all(col in mapping for col in expected):
                        rows = list(reader)
                        produtos_lidos = []
                        for row in rows:
                            try:
                                sku = str(row.get(mapping['COD_PRODUTO'], '')).strip()
                                nome = str(row.get(mapping['NOMEPRODUTOECOMM'], '')).strip()
                                ean = str(row.get(mapping['COD_BARRAS'], '')).strip()
                                imagem = str(row.get(mapping['URLECOMMERCEIMG'], '')).strip()
                                url = str(row.get(mapping['PRODUCTURL'], '')).strip()

                                # Ignora linhas claramente inválidas (sem URL ou com marcador 0/-)
                                if not url or url in ('0', '-'):
                                    continue

                                produtos_lidos.append({
                                    'sku': sku,
                                    'nome': nome,
                                    'ean': ean,
                                    'imagem': imagem,
                                    'url': url
                                })
                            except Exception:
                                # Pula linha problemática, segue nas demais
                                continue

                        if produtos_lidos:
                            produtos = produtos_lidos
                            print("✓ CSV carregado com sucesso!")
                            print(f"  - Arquivo: {os.path.basename(csv_path)}")
                            print(f"  - Encoding: {encoding}")
                            print(f"  - Delimitador: '{delimiter}'")
                            print(f"  - Total de produtos válidos: {len(produtos)}")
                            if produtos:
                                print(f"  - Exemplo: {produtos[0]['nome'][:50]}...")

                            _produtos_cache = produtos
                            _cache_timestamp = time.time()
                            return produtos
                        else:
                            # Mesmo com cabeçalhos válidos, não havia linhas úteis
                            continue

            except UnicodeDecodeError:
                continue
            except Exception as e:
                # Mantém a estratégia de continuar tentando, mas com um pouco de diagnóstico
                continue

    print("✗ Não foi possível ler o arquivo CSV.")
    print("  Verifique se as colunas estão corretas (e.g.:)")
    print("  COD_PRODUTO, NOMEPRODUTOECOMM, COD_BARRAS, URLECOMMERCEIMG, PRODUCTURL")
    if last_detected_headers is not None:
        print("  Cabeçalhos detectados na última tentativa:")
        print("  ", last_detected_headers)
    print(f"  Arquivo tentado: {csv_path}")
    return produtos

# --- FUNÇÃO PARA BUSCAR PRODUTO POR SKU, EAN OU URL ---
def buscar_produto(termo_busca):
    """
    Busca produto por SKU (COD_PRODUTO), EAN (COD_BARRAS) ou URL na planilha
    """
    produtos = carregar_produtos_planilha()
    termo_busca = termo_busca.strip().lower()
    
    for produto in produtos:
        if (produto['sku'].lower() == termo_busca or 
            produto['ean'].lower() == termo_busca or
            produto['url'].lower() == termo_busca or
            termo_busca in produto['nome'].lower()):
            return produto
    
    return None

# --- FUNÇÃO AUXILIAR PARA ADICIONAR UTM ---
def adicionar_utm_na_url(url_original, utm_source, utm_medium, utm_campaign):
    """
    Adiciona os parâmetros UTM à URL do produto.
    """
    utm_source_encoded = quote_plus(utm_source)
    utm_medium_encoded = quote_plus(utm_medium)
    utm_campaign_encoded = quote_plus(utm_campaign)
    
    separador = '&' if '?' in url_original else '?'
    utm_params = f"utm_source={utm_source_encoded}&utm_medium={utm_medium_encoded}&utm_campaign={utm_campaign_encoded}"
    return f"{url_original}{separador}{utm_params}"

# --- LÓGICA DE BUSCA DE PRODUTOS ---
def buscar_produtos(urls, template_base_html, utm_source="email-mkt", utm_campaign="cupom+15+novo+site"):
    """
    Recebe URLs e o HTML do template já montado,
    e insere apenas o grid de produtos.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("log-level=3")

    print("Configurando o driver do Chrome...")
    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    except Exception as e:
        print(f"Ocorreu um erro ao iniciar o driver: {e}")
        return f"<h1>Erro ao iniciar o navegador: {e}</h1>"

    todos_os_produtos_html = []
    contador_produto = 0
    
    for url in urls:
        if not url.strip():
            continue
        
        contador_produto += 1
        print(f"Processando URL {contador_produto}: {url.split('/')[-1]}")
        
        # Adiciona um limite de segurança
        if contador_produto > 50:
            print(f"Limite de 50 produtos atingido. Parando processamento.")
            break
            
        try:
            driver.get(url)
            time.sleep(3)

            html_completo = driver.page_source
            soup = BeautifulSoup(html_completo, 'html.parser')

            # --- Extração dos dados ---
            nome_produto_tag = soup.select_one('h1')
            nome_produto = nome_produto_tag.text.strip().title() if nome_produto_tag else "Produto Genérico"

            imagem_tag = soup.select_one('div.product-image-gallery-active-image img')
            url_imagem = imagem_tag['src'] if imagem_tag else "https://via.placeholder.com/120"

            preco_por_tag = soup.select_one('.product-renderer-active-price-wrapper span')
            preco_por_texto = preco_por_tag.text.strip() if preco_por_tag else "0,00"

            preco_de_tag = soup.select_one('p.text-full-price')
            preco_de_texto = preco_de_tag.text.strip() if preco_de_tag else ""

            preco_por_num = float(re.sub(r'[^\d,]', '', preco_por_texto).replace(',', '.'))
            preco_de_num = 0.0
            if preco_de_texto:
                preco_de_num = float(re.sub(r'[^\d,]', '', preco_de_texto).replace(',', '.'))

            porcentagem_desconto = 0
            if preco_de_num > preco_por_num:
                porcentagem_desconto = int(((preco_de_num - preco_por_num) / preco_de_num) * 100)

            preco_por_formatado = f"{preco_por_num:.2f}".replace('.', ',')
            preco_de_formatado = f"{preco_de_num:.2f}".replace('.', ',')

            utm_medium_automatico = f"produto {contador_produto:02d}"
            url_com_utm = adicionar_utm_na_url(url, utm_source, utm_medium_automatico, utm_campaign)

            html_bloco_desconto = ""
            html_selo_oferta = ""
            if porcentagem_desconto > 0:
                html_selo_oferta = '<tr><td align="left" valign="top" style="padding-bottom: 8px;"><span style="background-color: #ffebee; color: #dc3545; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: bold; font-family: \'Roboto\', Arial, sans-serif;">Oferta</span></td></tr>'
                html_bloco_desconto = f'<tr><td style="padding-bottom: 4px; text-align:left;"><table class="price-table" border="0" cellpadding="0" cellspacing="0" style="width:auto; margin:0;"><tbody><tr><td align="left" valign="middle" style="white-space:nowrap;"><span style="text-decoration: line-through; color: #6c757d; font-size: 12px; font-family: \'Roboto\', Arial, sans-serif;">R$ {preco_de_formatado}</span></td><td align="left" valign="middle" style="padding-left: 10px; white-space:nowrap;"><span style="background-color: #ffebee; color: #dc3545; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: bold; font-family: \'Roboto\', Arial, sans-serif;">-{porcentagem_desconto}%</span></td></tr></tbody></table></td></tr>'

            template_produto = f"""<div class="column" style="display: inline-block; width: 50%; max-width: 300px; vertical-align: top; box-sizing: border-box; padding: 4px;">
                <table class="product-card-table" width="100%" border="0" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; padding: 12px; text-align: left; height: 172px; box-sizing: border-box;">
                    <tbody><tr><td class="product-image-cell" valign="top" align="center" style="width: 120px;"><table width="100%" border="0" cellpadding="0" cellspacing="0"><tbody>{html_selo_oferta}<tr><td align="center" valign="top"><a target="_blank" href="{url_com_utm}"><img alt="{nome_produto}" style="display: block; margin: 0px auto; max-width: 120px;" src="{url_imagem}" /></a></td></tr></tbody></table></td><td class="product-info-cell" valign="top" align="left" style="text-align:left; padding:12px 0 0 12px;"><table width="100%" border="0" cellpadding="0" cellspacing="0"><tbody><tr><td style="font-size: 12px; font-weight: 700; color: #212529; font-family: 'Roboto', Arial, sans-serif; padding-bottom: 12px; height: 48px; vertical-align: top;">{nome_produto}</td></tr>{html_bloco_desconto}<tr><td style="font-size: 16px; font-weight: 700; color: #212529; font-family: 'Roboto', Arial, sans-serif; padding-bottom: 12px;">R$ {preco_por_formatado}</td></tr><tr><td><a target="_blank" style="background-color:#ff0000;border-radius:50px;color:#ffffff;display:block;font-family:'Roboto', Arial, sans-serif;font-size:12px;font-weight:bold;height:28px;line-height:28px;text-align:center;text-decoration:none;width:100%;-webkit-text-size-adjust:none;" href="{url_com_utm}">Ver Produto</a></td></tr></tbody></table></td></tr></tbody></table></div>"""
            todos_os_produtos_html.append(template_produto)
            
            print(f"Produto {contador_produto} processado com sucesso: {nome_produto}")
            
        except Exception as e:
            print(f"Erro ao processar a URL {url}: {e}")
            todos_os_produtos_html.append(f"<div>Erro ao buscar produto: {url}</div>")

    driver.quit()
    print("Navegador fechado.")
    print(f"Total de produtos processados: {len(todos_os_produtos_html)}")

    html_final_dos_produtos = '\n'.join(todos_os_produtos_html)
    
    # Verifica se o placeholder existe no template
    if '{{PRODUTOS_PLACEHOLDER}}' in template_base_html:
        email_final_html = template_base_html.replace('{{PRODUTOS_PLACEHOLDER}}', html_final_dos_produtos)
    elif '<!-- PRODUTOS -->' in template_base_html:
        email_final_html = template_base_html.replace('<!-- PRODUTOS -->', html_final_dos_produtos)
    elif '<!-- PRODUTOS_AQUI -->' in template_base_html:
        email_final_html = template_base_html.replace('<!-- PRODUTOS_AQUI -->', html_final_dos_produtos)
    else:
        # Debug: mostra onde deveria estar o placeholder
        print("AVISO: Nenhum placeholder encontrado no template!")
        print("Procurando por: '{{PRODUTOS_PLACEHOLDER}}', '<!-- PRODUTOS -->' ou '<!-- PRODUTOS_AQUI -->'")
        print("Adicionando produtos no final do template...")
        email_final_html = template_base_html + html_final_dos_produtos

    return email_final_html

# --- ROTAS DO SITE ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/buscar-sugestoes', methods=['POST'])
def buscar_sugestoes():
    """
    API para buscar sugestões de produtos - busca 100% EXATA
    Só mostra produtos que correspondem EXATAMENTE ao termo digitado
    """
    data = request.get_json()
    termo_busca = data.get('termo', '').strip()
    
    if not termo_busca:
        return jsonify({
            'success': True,
            'sugestoes': []
        })
    
    # Se for numérico, aceita 1+ caracteres, senão 2+
    is_numerico = termo_busca.isdigit()
    min_chars = 1 if is_numerico else 2
    
    if len(termo_busca) < min_chars:
        return jsonify({
            'success': True,
            'sugestoes': []
        })
    
    produtos = carregar_produtos_planilha()
    sugestoes = []
    termo_lower = termo_busca.lower()
    
    for produto in produtos:
        # Busca 100% EXATA por SKU ou EAN - só mostra se for idêntico
        if (produto['sku'].lower() == termo_lower or 
            produto['ean'].lower() == termo_lower):
            sugestoes.append(produto)
            
        # Limita a 10 sugestões
        if len(sugestoes) >= 10:
            break
    
    return jsonify({
        'success': True,
        'sugestoes': sugestoes
    }), 200, {'Content-Type': 'application/json; charset=utf-8'}

@app.route('/buscar-produto', methods=['POST'])
def buscar_produto_api():
    """
    API para buscar produto por SKU, EAN ou URL (busca exata)
    """
    data = request.get_json()
    termo_busca = data.get('termo', '').strip()
    
    if not termo_busca:
        return jsonify({'error': 'Termo de busca vazio'}), 400
    
    # Tenta buscar na planilha - busca exata
    produtos = carregar_produtos_planilha()
    termo_lower = termo_busca.lower()
    
    for produto in produtos:
        if (produto['sku'].lower() == termo_lower or 
            produto['ean'].lower() == termo_lower or
            produto['url'].lower() == termo_lower):
            return jsonify({
                'success': True,
                'produto': produto,
                'fonte': 'planilha'
            }), 200, {'Content-Type': 'application/json; charset=utf-8'}
    
    # Se não encontrar na planilha e for uma URL válida
    if termo_busca.startswith('http'):
        return jsonify({
            'success': True,
            'produto': {
                'url': termo_busca,
                'nome': 'Produto via URL',
                'imagem': 'https://via.placeholder.com/120',
                'sku': 'URL',
                'ean': '-'
            },
            'fonte': 'url'
        }), 200, {'Content-Type': 'application/json; charset=utf-8'}
    
    return jsonify({
        'success': False,
        'error': 'Produto não encontrado'
    }), 404

@app.route('/gerar', methods=['POST'])
def gerar_email():
    try:
        # Pega os dados do formulário (agora vem como JSON com lista de produtos)
        data = request.get_json()
        
        if not data:
            print("ERRO: Nenhum dado recebido no request")
            return jsonify({
                'success': False,
                'error': 'Nenhum dado recebido'
            }), 400
        
        produtos_selecionados = data.get('produtos', [])
        
        if not produtos_selecionados:
            print("ERRO: Nenhum produto selecionado")
            return jsonify({
                'success': False,
                'error': 'Nenhum produto selecionado'
            }), 400
        
        lista_urls = [p['url'] for p in produtos_selecionados]
        
        utm_source = data.get('utm_source', 'email-mkt')
        utm_campaign = data.get('utm_campaign', 'sem-campanha')
        bloco_03_selecionado = data.get('componente_bloco_03')
        bloco_05_selecionado = data.get('componente_bloco_05')

        print(f"✓ Recebidos {len(lista_urls)} produtos para processar.")
        print(f"✓ UTM Source: {utm_source}")
        print(f"✓ UTM Campaign: {utm_campaign}")
        print(f"✓ Componente Bloco 03: {bloco_03_selecionado}")
        print(f"✓ Componente Bloco 05: {bloco_05_selecionado}")
        
        # Renderiza o template base
        print("→ Renderizando template base...")
        template_para_produtos = render_template(
            'email_layout.html', 
            componente_bloco_03=bloco_03_selecionado, 
            componente_bloco_05=bloco_05_selecionado
        )
        
        # Busca os produtos
        print("→ Iniciando busca de produtos...")
        html_gerado = buscar_produtos(
            lista_urls, 
            template_para_produtos, 
            utm_source, 
            utm_campaign
        )
        
        print("✓ Email gerado com sucesso!")
        
        # Salva o HTML gerado na sessão ou retorna URL para resultado
        # Vamos retornar o HTML diretamente para o frontend redirecionar
        return jsonify({
            'success': True,
            'redirect': '/resultado',
            'html': html_gerado
        })
        
    except Exception as e:
        print(f"✗ ERRO CRÍTICO na rota /gerar: {str(e)}")
        import traceback
        print(traceback.format_exc())
        
        return jsonify({
            'success': False,
            'error': f'Erro ao gerar email: {str(e)}'
        }), 500

@app.route('/resultado')
def resultado():
    """
    Página de resultado que mostra o email gerado
    """
    # O HTML será passado via POST do frontend
    return render_template('resultado.html')

# --- CARREGAMENTO INICIAL DO CACHE ---
print("\n" + "="*60)
print("🚀 Iniciando Email Marketing Generator...")
print("="*60)

# Carrega produtos no cache ao iniciar o app
print("\n→ Pré-carregando catálogo de produtos...")
produtos_iniciais = carregar_produtos_planilha()
if produtos_iniciais:
    print(f"✓ Cache inicial criado com {len(produtos_iniciais)} produtos")
    if produtos_iniciais:
        print(f"  Exemplo: {produtos_iniciais[0]['nome'][:60]}...")
else:
    print("⚠ Nenhum produto carregado no cache inicial")

print("\n" + "="*60)
print("✓ App pronto para uso!")
print("="*60 + "\n")

# --- Inicia o servidor ---
if __name__ == '__main__':
   app.run(debug=True)