"""Secrets — integração com provedores de segredos.

Módulos disponíveis:
    - gcp_secrets: Integração com Google Cloud Secret Manager
    - env_secrets: Fallback para variáveis de ambiente (dev only)
"""

from __future__ import annotations

from app.infra.secrets.env_secrets import EnvSecretProvider
from app.infra.secrets.gcp_secrets import (
    GCPSecretProvider,
    get_secret,
    get_secret_async,
)

__all__ = [
    "EnvSecretProvider",
    "GCPSecretProvider",
    "get_secret",
    "get_secret_async",
]
