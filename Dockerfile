# ─────────────────────────────────────────────────────────
# Dockerfile — Atende_Pyloto
# Container otimizado para Cloud Run
# ─────────────────────────────────────────────────────────

# Usar imagem slim para reduzir tamanho e superfície de ataque
FROM python:3.12-slim

# Variáveis de ambiente para Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

# Diretório de trabalho
WORKDIR /app

# Instalar dependências de sistema mínimas
# - curl: para health checks
# - dumb-init: para signal handling correto em containers
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copiar código fonte e arquivos de configuração
COPY pyproject.toml README.md /app/
COPY src/ /app/src/

# Instalar dependências Python
RUN pip install --upgrade pip \
    && pip install .

# Criar usuário não-root para segurança
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash appuser \
    && chown -R appuser:appgroup /app

# Trocar para usuário não-root
USER appuser

# Expor porta padrão do Cloud Run
EXPOSE 8080

# Health check para Cloud Run e orquestradores
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Usar dumb-init para signal handling correto
# uvicorn com workers configuráveis via env
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["sh", "-c", "uvicorn app.app:app --host 0.0.0.0 --port ${PORT:-8080} --workers ${UVICORN_WORKERS:-1} --no-access-log"]
