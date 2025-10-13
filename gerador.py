import time
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuração do Selenium ---
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("log-level=3") # Adicionado para um output mais limpo

print("Configurando o driver do Chrome...")
try:
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
except Exception as e:
    print(f"Ocorreu um erro ao iniciar o driver: {e}")
    exit()

# --- NOVO: Carrega o template do e-mail ---
try:
    with open('email_base.html', 'r', encoding='utf-8') as f:
        template_email_completo = f.read()
    print("Template 'email_base.html' carregado com sucesso.")
except FileNotFoundError:
    print("Erro: O arquivo 'email_base.html' não foi encontrado no mesmo diretório do script.")
    exit()


# --- LISTA DE PRODUTOS PARA BUSCAR ---
# COLOQUE AS URLs DOS PRODUTOS AQUI
urls = [
    "https://www.superkoch.com.br/produtos/7076192/saponaceo-ype-multiuso-cremoso-original-300ml",
    "https://www.superkoch.com.br/produtos/7073800/papel-toalha-mili-55-folhas-com-2-unidades",
    "https://www.superkoch.com.br/produtos/7071227/lava-roupas-em-po-hipoalergenico-optical-wash-girando-sol-16kg",
    "https://www.superkoch.com.br/produtos/7064881/bebida-lactea-nescau-180ml"
]

todos_os_produtos_html = []
total_urls = len(urls)

try:
    # Loop principal para buscar informações de cada produto
    for i, url in enumerate(urls):
        print("-" * 50)
        print(f"Processando URL {i + 1}/{total_urls}: {url.split('/')[-1]}")

        try:
            driver.get(url)
            # Espera um pouco para garantir que o JavaScript carregue os preços
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

            # Limpeza e cálculo dos preços e desconto
            preco_por_num = float(re.sub(r'[^\d,]', '', preco_por_texto).replace(',', '.'))
            preco_de_num = 0.0
            if preco_de_texto:
                preco_de_num = float(re.sub(r'[^\d,]', '', preco_de_texto).replace(',', '.'))

            porcentagem_desconto = 0
            if preco_de_num > preco_por_num:
                porcentagem_desconto = int(((preco_de_num - preco_por_num) / preco_de_num) * 100)

            preco_por_formatado = f"{preco_por_num:.2f}".replace('.', ',')
            preco_de_formatado = f"{preco_de_num:.2f}".replace('.', ',')

            # Geração condicional do HTML de desconto
            html_bloco_desconto = ""
            html_selo_oferta = ""
            if porcentagem_desconto > 0:
                html_selo_oferta = """
                <tr>
                    <td align="left" valign="top" style="padding-bottom: 8px;"><span style="background-color: #ffebee; color: #dc3545; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: bold; font-family: 'Roboto', Arial, sans-serif;">Oferta</span></td>
                </tr>
                """
                html_bloco_desconto = f"""
                <tr>
                    <td style="padding-bottom: 4px; text-align:left;">
                        <table class="price-table" border="0" cellpadding="0" cellspacing="0" style="width:auto; margin:0;">
                            <tbody>
                                <tr>
                                    <td align="left" valign="middle" style="white-space:nowrap;"><span style="text-decoration: line-through; color: #6c757d; font-size: 12px; font-family: 'Roboto', Arial, sans-serif;">R$ {preco_de_formatado}</span></td>
                                    <td align="left" valign="middle" style="padding-left: 10px; white-space:nowrap;"><span style="background-color: #ffebee; color: #dc3545; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: bold; font-family: 'Roboto', Arial, sans-serif;">-{porcentagem_desconto}%</span></td>
                                </tr>
                            </tbody>
                        </table>
                    </td>
                </tr>
                """

            # Template para cada card de produto
            template_produto = f"""<div class="column" style="display: inline-block; width: 50%; max-width: 300px; vertical-align: top; box-sizing: border-box; padding: 4px;">
                <table class="product-card-table" width="100%" border="0" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; padding: 12px; text-align: left; height: 172px; box-sizing: border-box;">
                    <tbody>
                        <tr>
                            <td class="product-image-cell" valign="top" align="center" style="width: 120px;">
                                <table width="100%" border="0" cellpadding="0" cellspacing="0">
                                    <tbody>
                                        {html_selo_oferta}
                                        <tr>
                                            <td align="center" valign="top">
                                                <a target="_blank" href="{url}"><img alt="{nome_produto}" style="display: block; margin: 0px auto; max-width: 120px;" src="{url_imagem}" /></a>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </td>
                            <td class="product-info-cell" valign="top" align="left" style="text-align:left; padding:12px 0 0 12px;">
                                <table width="100%" border="0" cellpadding="0" cellspacing="0">
                                    <tbody>
                                        <tr>
                                            <td style="font-size: 12px; font-weight: 700; color: #212529; font-family: 'Roboto', Arial, sans-serif; padding-bottom: 12px; height: 48px; vertical-align: top;">{nome_produto}</td>
                                        </tr>
                                        {html_bloco_desconto}
                                        <tr>
                                            <td style="font-size: 16px; font-weight: 700; color: #212529; font-family: 'Roboto', Arial, sans-serif; padding-bottom: 12px;">R$ {preco_por_formatado}</td>
                                        </tr>
                                        <tr>
                                            <td><a target="_blank" style="background-color:#ff0000;border-radius:50px;color:#ffffff;display:block;font-family:'Roboto', Arial, sans-serif;font-size:12px;font-weight:bold;height:28px;line-height:28px;text-align:center;text-decoration:none;width:100%;-webkit-text-size-adjust:none;" href="{url}">Ver Produto</a></td>
                                        </tr>
                                    </tbody>
                                </table>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>"""

            # Adiciona o HTML do produto à lista
            todos_os_produtos_html.append(template_produto)

        except Exception as e:
            print(f"Erro ao processar a URL {url}: {e}")

    # --- NOVO: Junta os cards e insere no template principal ---
    # Junta todos os cards de produto em uma única string
    html_final_dos_produtos = '\n'.join(todos_os_produtos_html)

    # Substitui o placeholder no template pelo HTML dos produtos
    email_final_html = template_email_completo.replace('<!-- PRODUTOS_AQUI -->', html_final_dos_produtos)

    # Salva o e-mail completo em um novo arquivo
    with open('email_gerado.html', 'w', encoding='utf-8') as f:
        f.write(email_final_html)

    print("\n✅ Sucesso! O arquivo 'email_gerado.html' foi criado com o layout completo e os produtos inseridos.")
    print("Você já pode usar este arquivo para sua campanha de e-mail.")

finally:
    print("Fechando o navegador.")
    driver.quit()