"""Settings de sessão/conversação.

Configurações para gerenciamento de sessões de atendimento.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from config.settings.base.core import BaseSettings

SessionStoreBackend = Literal["memory", "redis", "firestore"]


@dataclass(frozen=True)
class SessionSettings:
    """Configurações de sessão/conversação.

    Attributes:
        timeout_seconds: Timeout de sessão inativa
        max_intents_per_session: Máximo de intents por sessão
        store_backend: Backend para armazenamento de sessão
    """

    timeout_seconds: int = 1800  # 30 min
    max_intents_per_session: int = 10
    store_backend: SessionStoreBackend = "memory"

    def validate(self, base: BaseSettings) -> list[str]:
        """Valida configurações de sessão.

        Args:
            base: BaseSettings para verificar ambiente.

        Returns:
            Lista de erros de validação.
        """
        errors: list[str] = []

        if self.timeout_seconds <= 0:
            errors.append("SESSION_TIMEOUT_SECONDS deve ser > 0")

        if self.max_intents_per_session < 1:
            errors.append("SESSION_MAX_INTENTS deve ser >= 1")

        valid_backends = {"memory", "redis", "firestore"}
        if self.store_backend not in valid_backends:
            errors.append(f"SESSION_STORE_BACKEND inválido: {self.store_backend}")

        if self.store_backend == "memory" and not base.is_development:
            errors.append("SESSION_STORE_BACKEND=memory proibido em staging/production")

        return errors


def _load_session_from_env() -> SessionSettings:
    """Carrega SessionSettings de variáveis de ambiente."""
    backend_str = os.getenv("SESSION_STORE_BACKEND", "memory").lower()
    backend: SessionStoreBackend = (
        backend_str if backend_str in ("memory", "redis", "firestore") else "memory"
    )
    return SessionSettings(
        timeout_seconds=int(os.getenv("SESSION_TIMEOUT_SECONDS", "1800")),
        max_intents_per_session=int(os.getenv("SESSION_MAX_INTENTS", "10")),
        store_backend=backend,
    )


@lru_cache(maxsize=1)
def get_session_settings() -> SessionSettings:
    """Retorna instância cacheada de SessionSettings."""
    return _load_session_from_env()
