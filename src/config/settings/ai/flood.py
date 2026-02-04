"""Settings de detecção de flood/spam.

Configurações para proteção contra abuso.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class FloodDetectionSettings:
    """Configurações de detecção de flood/spam.

    Attributes:
        threshold: Número de mensagens para ativar proteção
        ttl_seconds: Janela de tempo para contagem
        enabled: Se detecção está habilitada
    """

    threshold: int = 10
    ttl_seconds: int = 60
    enabled: bool = True

    def validate(self) -> list[str]:
        """Valida configurações de flood detection.

        Returns:
            Lista de erros de validação.
        """
        errors: list[str] = []

        if self.threshold < 1:
            errors.append("FLOOD_THRESHOLD deve ser >= 1")

        if self.ttl_seconds < 1:
            errors.append("FLOOD_TTL_SECONDS deve ser >= 1")

        return errors


def _load_flood_detection_from_env() -> FloodDetectionSettings:
    """Carrega FloodDetectionSettings de variáveis de ambiente."""
    return FloodDetectionSettings(
        threshold=int(os.getenv("FLOOD_THRESHOLD", "10")),
        ttl_seconds=int(os.getenv("FLOOD_TTL_SECONDS", "60")),
        enabled=os.getenv("FLOOD_DETECTION_ENABLED", "true").lower() in ("true", "1"),
    )


@lru_cache(maxsize=1)
def get_flood_detection_settings() -> FloodDetectionSettings:
    """Retorna instância cacheada de FloodDetectionSettings."""
    return _load_flood_detection_from_env()
