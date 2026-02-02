FROM python:3.12-slim

WORKDIR /app

# 1. Instala dependências via requirements.txt (mais rápido que Poetry)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copia código fonte
COPY src/ ./src/
COPY main.py ./
COPY serviceAccountKey.json ./

# 3. Configura PYTHONPATH para imports funcionarem
ENV PYTHONPATH=/app/src

# 4. Usuário não-root para segurança
RUN useradd --create-home appuser
USER appuser

# 5. Cloud Run define a variável PORT (padrão 8080)
ENV PORT=8080
EXPOSE 8080

# 6. Comando usando $PORT do ambiente
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
