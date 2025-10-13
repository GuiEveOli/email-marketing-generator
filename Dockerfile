# 1. Use uma imagem oficial do Python como base
FROM python:3.10-slim

# 2. Defina o diretório de trabalho dentro do contêiner
WORKDIR /app

# 3. Instale o Google Chrome e outras dependências do sistema
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    --no-install-recommends && \
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb

# 4. Copie o arquivo de dependências e instale as bibliotecas Python
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copie o resto dos arquivos do seu aplicativo para o contêiner
COPY . .

# 6. Exponha a porta em que o aplicativo será executado
EXPOSE 10000

# 7. Comando para iniciar o aplicativo usando Gunicorn
CMD ["gunicorn", "--workers=2", "--bind", "0.0.0.0:10000", "app:app"]