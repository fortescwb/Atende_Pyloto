"""Settings de OpenAI.

Configurações para integração com OpenAI API.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class OpenAISettings:
    """Configurações do OpenAI.

    Attributes:
        api_key: Chave da API OpenAI
        model: Modelo padrão a usar
        timeout_seconds: Timeout para chamadas à API
        max_retries: Máximo de tentativas em caso de erro
        enabled: Se integração OpenAI está habilitada
    """

    api_key: str = ""
    model: str = "gpt-4o-mini"
    timeout_seconds: float = 30.0
    max_retries: int = 3
    enabled: bool = True

    def validate(self) -> list[str]:
        """Valida configurações do OpenAI.

        Returns:
            Lista de erros de validação.
        """
        errors: list[str] = []

        if self.enabled and not self.api_key:
            errors.append("OPENAI_API_KEY não configurado mas OPENAI_ENABLED=true")

        if self.timeout_seconds <= 0:
            errors.append("OPENAI_TIMEOUT_SECONDS deve ser > 0")

        if self.max_retries < 0:
            errors.append("OPENAI_MAX_RETRIES deve ser >= 0")

        return errors


def _load_openai_from_env() -> OpenAISettings:
    """Carrega OpenAISettings de variáveis de ambiente."""
    return OpenAISettings(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30")),
        max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3")),
        enabled=os.getenv("OPENAI_ENABLED", "true").lower() in ("true", "1", "yes"),
    )


@lru_cache(maxsize=1)
def get_openai_settings() -> OpenAISettings:
    """Retorna instância cacheada de OpenAISettings."""
    return _load_openai_from_env()
