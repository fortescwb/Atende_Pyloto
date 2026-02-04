"""Settings base do Atende_Pyloto.

Configurações comuns a todos os canais e serviços.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

Environment = Literal["development", "staging", "production"]


@dataclass(frozen=True)
class BaseSettings:
    """Configurações base do sistema.

    Attributes:
        environment: Ambiente de execução (development|staging|production)
        service_name: Nome do serviço para logs e tracing
        debug: Modo debug ativo
        zero_trust_mode: Modo zero-trust (validação rigorosa)
        gcp_project: ID do projeto GCP
        redis_url: URL de conexão Redis (Upstash)
    """

    # Ambiente
    environment: Environment = "development"
    service_name: str = "atende-pyloto"
    debug: bool = False
    zero_trust_mode: bool = True

    # GCP
    gcp_project: str = ""

    # Redis (Upstash)
    redis_url: str = ""

    @property
    def is_production(self) -> bool:
        """Retorna True se ambiente é produção."""
        return self.environment == "production"

    @property
    def is_staging(self) -> bool:
        """Retorna True se ambiente é staging."""
        return self.environment == "staging"

    @property
    def is_development(self) -> bool:
        """Retorna True se ambiente é desenvolvimento."""
        return self.environment == "development"

    def validate(self) -> list[str]:
        """Valida configurações base.

        Returns:
            Lista de erros (vazia = OK).
        """
        errors: list[str] = []

        valid_envs = {"development", "staging", "production"}
        if self.environment not in valid_envs:
            errors.append(f"ENVIRONMENT inválido: {self.environment}")

        if not self.service_name:
            errors.append("SERVICE_NAME não pode ser vazio")

        return errors


def _parse_environment(env_str: str) -> Environment:
    """Converte string de ambiente para tipo Environment."""
    env_lower = env_str.lower()
    if env_lower in ("production", "prod"):
        return "production"
    if env_lower in ("staging", "stage"):
        return "staging"
    return "development"


def _load_base_from_env() -> BaseSettings:
    """Carrega BaseSettings de variáveis de ambiente."""
    return BaseSettings(
        environment=_parse_environment(os.getenv("ENVIRONMENT", "development")),
        service_name=os.getenv("SERVICE_NAME", "atende-pyloto"),
        debug=os.getenv("DEBUG", "").lower() in ("true", "1", "yes"),
        zero_trust_mode=os.getenv("ZERO_TRUST_MODE", "true").lower() in ("true", "1"),
        gcp_project=os.getenv("GCP_PROJECT", os.getenv("GOOGLE_CLOUD_PROJECT", "")),
        redis_url=os.getenv("REDIS_URL", ""),
    )


@lru_cache(maxsize=1)
def get_base_settings() -> BaseSettings:
    """Retorna instância cacheada de BaseSettings."""
    return _load_base_from_env()
