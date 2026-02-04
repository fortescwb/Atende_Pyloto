"""Entrypoint da aplicação Atende_Pyloto.

Este módulo é o ponto de entrada principal do serviço.
Inicializa o bootstrap e expõe a aplicação ASGI (FastAPI).

Uso (produção):
    uvicorn app.app:app --host 0.0.0.0 --port 8080

Uso (desenvolvimento):
    uvicorn app.app:app --reload --host 0.0.0.0 --port 8080

Cloud Run:
    O container deve expor a porta 8080 (padrão do Cloud Run).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import create_api_router
from app.bootstrap import initialize_app
from config.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# Inicializar logging e dependências ANTES de qualquer import que use logger
initialize_app()

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia ciclo de vida da aplicação.

    Startup:
    - Inicializa conexões (Redis, Firestore)
    - Valida configurações

    Shutdown:
    - Fecha conexões gracefully
    - Flush de logs/métricas
    """
    # Startup
    logger.info("app_starting", extra={"service": "atende-pyloto"})

    # TODO: Inicializar conexões quando stores forem implementados
    # await initialize_stores()

    yield

    # Shutdown
    logger.info("app_shutting_down", extra={"service": "atende-pyloto"})

    # TODO: Fechar conexões gracefully
    # await close_stores()


def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI.

    Returns:
        Aplicação FastAPI configurada.
    """
    fastapi_app = FastAPI(
        title="Atende_Pyloto",
        description="Núcleo de atendimento e automação omnichannel",
        version="1.0.0",
        lifespan=lifespan,
        # Desabilita docs em produção (habilitar via env se necessário)
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS - configurar conforme necessidade
    # Em produção, restringir origins
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Restringir em produção
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Registra todas as rotas
    fastapi_app.include_router(create_api_router())

    logger.info("app_configured", extra={"service": "atende-pyloto"})

    return fastapi_app


# Aplicação ASGI exposta para uvicorn
app = create_app()


def main() -> None:
    """Entrypoint para execução direta (desenvolvimento)."""
    import uvicorn

    logger.info("Starting Atende_Pyloto in development mode")
    uvicorn.run(
        "app.app:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
    )


if __name__ == "__main__":
    main()
