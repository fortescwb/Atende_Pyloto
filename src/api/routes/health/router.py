"""Endpoints de health check para Cloud Run.

Endpoints:
- GET /health: liveness probe (serviço está rodando)
- GET /ready: readiness probe (serviço está pronto para receber tráfego)

Esses endpoints são usados pelo Cloud Run para determinar
se o container está saudável e pronto.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Resposta do health check."""

    status: str
    service: str
    timestamp: str
    version: str = "1.0.0"


class ReadyResponse(BaseModel):
    """Resposta do readiness check."""

    status: str
    checks: dict[str, Any]
    timestamp: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe — verifica se o serviço está rodando.

    Returns:
        Status do serviço.
    """
    return HealthResponse(
        status="healthy",
        service="atende-pyloto",
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/ready", response_model=ReadyResponse)
async def readiness_check() -> ReadyResponse:
    """Readiness probe — verifica se o serviço está pronto.

    Verifica conexões críticas (Redis, Firestore, etc.)
    antes de aceitar tráfego.

    Returns:
        Status e detalhes de cada dependência.
    """
    checks: dict[str, Any] = {}

    # TODO: Adicionar verificações de dependências quando implementadas
    # - Redis/Upstash: ping
    # - Firestore: health check
    # - OpenAI: api status (opcional)

    # Por enquanto, apenas verifica que o serviço está respondendo
    checks["app"] = {"status": "ok"}

    all_ok = all(c.get("status") == "ok" for c in checks.values())

    return ReadyResponse(
        status="ready" if all_ok else "degraded",
        checks=checks,
        timestamp=datetime.now(UTC).isoformat(),
    )
