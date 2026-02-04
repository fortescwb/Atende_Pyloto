"""Agregador de rotas — registra todos os routers por canal.

Este módulo é responsável por criar o router principal da API
e incluir todos os sub-routers de cada canal.

Uso:
    from api.routes import create_api_router

    app = FastAPI()
    app.include_router(create_api_router())
"""

from __future__ import annotations

from fastapi import APIRouter

from api.routes.health.router import router as health_router
from api.routes.whatsapp.router import router as whatsapp_router


def create_api_router() -> APIRouter:
    """Cria router principal com todos os sub-routers registrados.

    Returns:
        APIRouter configurado com todos os endpoints.
    """
    api_router = APIRouter()

    # Health checks (sem prefixo para /health e /ready na raiz)
    api_router.include_router(health_router, tags=["health"])

    # WhatsApp
    api_router.include_router(
        whatsapp_router,
        prefix="/webhook/whatsapp",
        tags=["whatsapp"],
    )

    # TODO: Adicionar outros canais conforme implementados
    # api_router.include_router(instagram_router, prefix="/webhook/instagram")
    # api_router.include_router(facebook_router, prefix="/webhook/facebook")

    return api_router
