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

print("Configurando o driver do Chrome...")
try:
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
except Exception as e:
    print(f"Ocorreu um erro ao iniciar o driver: {e}")
    exit()

# COLOQUE A URL DO PRODUTO AQUI
urls = [
    "https://www.superkoch.com.br/produtos/7076192/saponaceo-ype-multiuso-cremoso-original-300ml",
    "https://www.superkoch.com.br/produtos/7073800/papel-toalha-mili-55-folhas-com-2-unidades"
]

todos_os_produtos_html = []
total_urls = len(urls)

try:
    # ==============================================================================
    # MUDANÇA 3: O LOOP PRINCIPAL
    # O 'for' vai executar o bloco de código abaixo para cada url na nossa lista.
    # Usamos 'enumerate' para ter um contador (i) e saber qual produto estamos processando.
    # ==============================================================================
    for i, url in enumerate(urls):
        print("-" * 50)
        print(f"Processando URL {i + 1}/{total_urls}: {url}")

        try:
            driver.get(url)
            time.sleep(3) # Espera pelo conteúdo dinâmico

            html_completo = driver.page_source
            soup = BeautifulSoup(html_completo, 'html.parser')

            # --- Extração dos dados ---
            nome_produto_tag = soup.select_one('h1') 
            nome_produto = nome_produto_tag.text.strip() if nome_produto_tag else "Produto Genérico"

            imagem_tag = soup.select_one('div.product-image-gallery-active-image img') 
            url_imagem = imagem_tag['src'] if imagem_tag else "https://via.placeholder.com/300"

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

            template_produto = f"""
            <div class="column" style="display: inline-block; width: 50%; max-width: 300px; vertical-align: top; box-sizing: border-box; padding: 4px;">
                <table class="product-card-table" width="100%" border="0" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; padding: 12px; text-align: left; height: 172px; box-sizing: border-box;">
                    <tbody>
                        <tr>
                            <td class="product-image-cell" valign="top" align="center" style="width: 120px;">
                                <table width="100%" border="0" cellpadding="0" cellspacing="0">
                                    <tbody>
                                        {html_selo_oferta}
                                        <tr>
                                            <td align="center" valign="top">
                                                <img alt="{nome_produto}" style="display: block; margin: 0px auto; max-width: 120px;" src="{url_imagem}" />
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </td>
                            <td class="product-info-cell" valign="top" align="left" style="text-align:left; padding:12px 0 0 12px;">
                                <table width="100%" border="0" cellpadding="0" cellspacing="0">
                                    <tbody>
                                        <tr>
                                            <td style="font-size: 12px; font-weight: 700; color: #212529; font-family: 'Roboto', Arial, sans-serif; padding-bottom: 12px;">{nome_produto}</td>
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
            </div>
            """

            # Adiciona o HTML do produto à lista
            todos_os_produtos_html.append(template_produto)

        except Exception as e:
            print(f"Erro ao processar a URL {url}: {e}")

    # Após o loop, gera o arquivo de preview com todos os produtos
    pagina_preview = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Preview dos Produtos</title></head>
    <body style="background-color: #f0f0f0; padding: 20px; font-family: sans-serif;">
        <h2 style="text-align: center;">Preview dos Blocos de Produtos</h2>
        {''.join(todos_os_produtos_html)}
        <hr style="margin: 40px 0;">
        <h2 style="text-align: center;">Código HTML para Copiar</h2>
        <textarea rows="25" style="width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; font-family: monospace;" onclick="this.select();">{''.join(todos_os_produtos_html).strip()}</textarea>
    </body>
    </html>
    """

    with open('produto_final.html', 'w', encoding='utf-8') as f:
        f.write(pagina_preview)

    print("\n✅ Sucesso! Arquivo 'produto_final.html' foi gerado.")
    print("Abra o arquivo para ver a pré-visualização e copiar o código dos produtos.")

finally:
    print("Fechando o navegador.")
    driver.quit()