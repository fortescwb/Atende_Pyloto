"""Settings de dedupe/idempotência.

Configurações para garantir processamento único de eventos.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from config.settings.base.core import BaseSettings

DedupeBackend = Literal["memory", "redis", "firestore"]


@dataclass(frozen=True)
class DedupeSettings:
    """Configurações de dedupe/idempotência.

    Attributes:
        backend: Backend para dedupe (memory|redis|firestore)
        ttl_seconds: TTL para entradas de dedupe
    """

    backend: DedupeBackend = "memory"
    ttl_seconds: int = 86400  # 24h

    def validate(self, base: BaseSettings) -> list[str]:
        """Valida configurações de dedupe.

        Args:
            base: BaseSettings para verificar ambiente.

        Returns:
            Lista de erros de validação.
        """
        errors: list[str] = []
        valid_backends = {"memory", "redis", "firestore"}

        if self.backend not in valid_backends:
            errors.append(f"DEDUPE_BACKEND inválido: {self.backend}")

        if self.backend == "memory" and not base.is_development:
            errors.append(
                "DEDUPE_BACKEND=memory proibido em staging/production. "
                "Use Redis ou Firestore."
            )

        if self.backend == "redis" and not base.redis_url:
            errors.append("DEDUPE_BACKEND=redis requer REDIS_URL configurado")

        if self.backend == "firestore" and not base.gcp_project:
            errors.append("DEDUPE_BACKEND=firestore requer GCP_PROJECT configurado")

        if self.ttl_seconds <= 0:
            errors.append("DEDUPE_TTL_SECONDS deve ser > 0")

        return errors


def _load_dedupe_from_env() -> DedupeSettings:
    """Carrega DedupeSettings de variáveis de ambiente."""
    backend_str = os.getenv("DEDUPE_BACKEND", "memory").lower()
    backend: DedupeBackend = (
        backend_str if backend_str in ("memory", "redis", "firestore") else "memory"
    )
    return DedupeSettings(
        backend=backend,
        ttl_seconds=int(os.getenv("DEDUPE_TTL_SECONDS", "86400")),
    )


@lru_cache(maxsize=1)
def get_dedupe_settings() -> DedupeSettings:
    """Retorna instância cacheada de DedupeSettings."""
    return _load_dedupe_from_env()
