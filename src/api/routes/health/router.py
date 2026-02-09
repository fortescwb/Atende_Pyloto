"""Endpoints de health check para Cloud Run."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Resposta do health check."""

    status: str
    service: str
    timestamp: str
    version: str = "1.0.0"


@dataclass(frozen=True, slots=True)
class DependencyCheck:
    """Resultado de checagem de dependência."""

    status: Literal["ok", "degraded", "failed"]
    latency_ms: float | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe — verifica se o serviço está rodando."""
    return HealthResponse(
        status="healthy",
        service="atende-pyloto",
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/ready")
async def readiness_check(request: Request) -> JSONResponse:
    """Readiness probe com verificação real de dependências críticas."""
    redis_check, firestore_check, openai_check = await asyncio.gather(
        _check_redis(getattr(request.app.state, "redis_client", None)),
        _check_firestore(getattr(request.app.state, "firestore_client", None)),
        _check_openai(getattr(request.app.state, "openai_client", None)),
    )

    critical_ok = redis_check.status == "ok" and firestore_check.status in {"ok", "degraded"}
    openai_ok = openai_check.status in {"ok", "degraded"}
    ready = critical_ok and openai_ok

    payload = {
        "status": "ready" if ready else "not_ready",
        "checks": {
            "redis": redis_check.as_dict(),
            "firestore": firestore_check.as_dict(),
            "openai": openai_check.as_dict(),
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }
    return JSONResponse(content=payload, status_code=200 if ready else 503)


async def _check_redis(redis_client: Any | None) -> DependencyCheck:
    if redis_client is None:
        return DependencyCheck(status="failed", error="not_configured")
    started_at = time.perf_counter()
    try:
        await asyncio.wait_for(redis_client.ping(), timeout=2.0)
    except TimeoutError:
        return DependencyCheck(status="failed", error="timeout")
    except Exception as exc:
        return DependencyCheck(status="failed", error=type(exc).__name__)
    latency_ms = (time.perf_counter() - started_at) * 1000
    return DependencyCheck(status="ok", latency_ms=round(latency_ms, 2))


async def _check_firestore(firestore_client: Any | None) -> DependencyCheck:
    if firestore_client is None:
        return DependencyCheck(status="failed", error="not_configured")
    started_at = time.perf_counter()
    try:
        exists = await asyncio.wait_for(
            asyncio.to_thread(_read_firestore_health_doc, firestore_client),
            timeout=3.0,
        )
    except TimeoutError:
        return DependencyCheck(status="failed", error="timeout")
    except Exception as exc:
        return DependencyCheck(status="failed", error=type(exc).__name__)
    latency_ms = (time.perf_counter() - started_at) * 1000
    status = "ok" if exists else "degraded"
    return DependencyCheck(status=status, latency_ms=round(latency_ms, 2))


def _read_firestore_health_doc(firestore_client: Any) -> bool:
    doc = firestore_client.collection("_health").document("check").get()
    return bool(getattr(doc, "exists", False))


async def _check_openai(openai_client: Any | None) -> DependencyCheck:
    if openai_client is None:
        return DependencyCheck(status="degraded", error="not_configured")
    started_at = time.perf_counter()
    try:
        await asyncio.wait_for(openai_client.models.list(), timeout=5.0)
    except TimeoutError:
        return DependencyCheck(status="degraded", error="timeout")
    except Exception as exc:
        logger.warning("readiness_openai_check_failed", extra={"error_type": type(exc).__name__})
        return DependencyCheck(status="degraded", error=type(exc).__name__)
    latency_ms = (time.perf_counter() - started_at) * 1000
    return DependencyCheck(status="ok", latency_ms=round(latency_ms, 2))
