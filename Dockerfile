# Extrator de Importação — Aconsult (mockup) — imagem para deploy na VPS.
# Mockup: imagem enxuta, um worker, sem hardening de produção. Ver DEPLOY.md.

FROM python:3.11-slim

# Boas práticas em container: sem .pyc, logs sem buffer (aparecem no `docker logs`).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Deps primeiro para aproveitar o cache de camadas do Docker.
# As versões de extração de PDF estão PINADAS (requirements.txt, spec §13):
# reproduzir exatamente o ambiente validado contra o corpus real.
# Obs.: os wheels de cryptography/Pillow/pdfminer resolvem em python:3.11-slim
# sem toolchain. Se algum pacote precisar compilar, adicione antes do pip:
#   RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
#       && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Só o necessário em runtime: o backend e o front-end estático.
# assets/ (fixtures de teste) e tests/ ficam de fora via .dockerignore.
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Porta do uvicorn (a VPS pode sobrescrever com -e PORT=...).
ENV PORT=8000
EXPOSE 8000

# ASGI de produção: SEM --reload. Um worker basta para o mockup; para escalar,
# acrescente --workers N (ex.: --workers 2) — o app não tem estado em memória.
# `sh -c` é necessário para expandir ${PORT} em runtime.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
