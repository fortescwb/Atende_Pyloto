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

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import create_api_router
from api.routes.whatsapp.webhook_runtime import drain_background_tasks
from app.bootstrap import initialize_app, validate_runtime_settings
from app.bootstrap.clients import create_async_redis_client, create_firestore_client
from config.logging import get_logger
from config.settings import get_openai_settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# Inicializar logging e dependências ANTES de qualquer import que use logger
initialize_app()

logger = get_logger(__name__)


async def _seed_firestore_health_doc(firestore_client: object) -> None:
    """Escreve documento mínimo de health para check de readiness."""

    def _write_doc() -> None:
        firestore_client.collection("_health").document("check").set(  # type: ignore[attr-defined]
            {
                "updated_at": datetime.now(UTC).isoformat(),
                "service": "atende-pyloto",
            }
        )

    await asyncio.to_thread(_write_doc)


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
    logger.info("app_starting", extra={"service": "atende-pyloto"})
    validate_runtime_settings()
    app.state.redis_client = None
    app.state.firestore_client = None
    app.state.openai_client = None

    try:
        app.state.redis_client = create_async_redis_client()
    except Exception as exc:
        logger.warning("redis_client_not_ready", extra={"error_type": type(exc).__name__})

    try:
        app.state.firestore_client = create_firestore_client()
        await _seed_firestore_health_doc(app.state.firestore_client)
    except Exception as exc:
        logger.warning("firestore_client_not_ready", extra={"error_type": type(exc).__name__})

    openai_settings = get_openai_settings()
    if openai_settings.enabled and openai_settings.api_key:
        try:
            from openai import AsyncOpenAI

            app.state.openai_client = AsyncOpenAI(api_key=openai_settings.api_key)
        except Exception as exc:
            logger.warning("openai_client_not_ready", extra={"error_type": type(exc).__name__})

    yield

    logger.info("app_shutting_down", extra={"service": "atende-pyloto"})
    await drain_background_tasks(timeout_seconds=30.0)
    redis_client = getattr(app.state, "redis_client", None)
    if redis_client is not None:
        close_async = getattr(redis_client, "aclose", None)
        close_sync = getattr(redis_client, "close", None)
        if callable(close_async):
            await close_async()
        elif callable(close_sync):
            await close_sync()


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
