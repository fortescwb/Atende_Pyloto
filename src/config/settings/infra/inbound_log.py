"""Settings de log inbound.

Configurações para rastro de mensagens inbound.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

LogBackend = Literal["memory", "redis", "firestore"]


@dataclass(frozen=True)
class InboundLogSettings:
    """Configurações de log de mensagens inbound.

    Attributes:
        backend: Backend para rastro (memory|redis|firestore)
        ttl_seconds: TTL para entradas de log
    """

    backend: LogBackend = "memory"
    ttl_seconds: int = 604800  # 7 dias

    def validate(self, redis_url: str, gcp_project: str, is_dev: bool) -> list[str]:
        """Valida configurações de log inbound.

        Args:
            redis_url: URL do Redis.
            gcp_project: Projeto GCP.
            is_dev: Se está em desenvolvimento.

        Returns:
            Lista de erros de validação.
        """
        errors: list[str] = []
        valid_backends = {"memory", "redis", "firestore"}

        if self.backend not in valid_backends:
            errors.append(f"INBOUND_LOG_BACKEND inválido: {self.backend}")

        if self.backend == "memory" and not is_dev:
            errors.append(
                "INBOUND_LOG_BACKEND=memory proibido em staging/production"
            )

        if self.backend == "redis" and not redis_url:
            errors.append("INBOUND_LOG_BACKEND=redis requer REDIS_URL")

        if self.backend == "firestore" and not gcp_project:
            errors.append("INBOUND_LOG_BACKEND=firestore requer GCP_PROJECT")

        return errors


def _load_inbound_log_from_env() -> InboundLogSettings:
    """Carrega InboundLogSettings de variáveis de ambiente."""
    backend_str = os.getenv("INBOUND_LOG_BACKEND", "memory").lower()
    backend: LogBackend = (
        backend_str if backend_str in ("memory", "redis", "firestore") else "memory"
    )

    return InboundLogSettings(
        backend=backend,
        ttl_seconds=int(os.getenv("INBOUND_LOG_TTL_SECONDS", "604800")),
    )


@lru_cache(maxsize=1)
def get_inbound_log_settings() -> InboundLogSettings:
    """Retorna instância cacheada de InboundLogSettings."""
    return _load_inbound_log_from_env()
