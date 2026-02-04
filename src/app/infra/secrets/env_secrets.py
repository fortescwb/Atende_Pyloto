"""Environment Secrets — provedor de secrets via variáveis de ambiente.

Fallback para desenvolvimento local. NÃO usar em staging/production.

Referência: REGRAS_E_PADROES.md § 7 — Segurança
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


class EnvSecretProvider:
    """Provedor de secrets usando variáveis de ambiente.

    ATENÇÃO: Usar apenas em desenvolvimento local.
    Em staging/production, use GCPSecretProvider.

    Args:
        prefix: Prefixo para variáveis de ambiente (default: "")
    """

    def __init__(self, prefix: str = "") -> None:
        self._prefix = prefix.upper().rstrip("_") + "_" if prefix else ""

    def _env_key(self, key: str) -> str:
        """Converte nome de secret para variável de ambiente."""
        # openai-api-key -> OPENAI_API_KEY
        env_key = key.upper().replace("-", "_")
        return f"{self._prefix}{env_key}"

    def get(self, key: str, default: str | None = None) -> str | None:
        """Obtém secret de variável de ambiente.

        Args:
            key: Nome do secret (ex.: openai-api-key)
            default: Valor padrão

        Returns:
            Valor ou default
        """
        env_key = self._env_key(key)
        value = os.getenv(env_key)
        if value is None:
            logger.debug("env_secret_not_found", extra={"key": key, "env_key": env_key})
            return default
        return value

    def require(self, key: str) -> str:
        """Obtém secret obrigatório de variável de ambiente.

        Args:
            key: Nome do secret

        Returns:
            Valor do secret

        Raises:
            ValueError: Se variável não definida
        """
        value = self.get(key)
        if value is None:
            env_key = self._env_key(key)
            msg = f"Variável de ambiente obrigatória não definida: {env_key}"
            raise ValueError(msg)
        return value

    @property
    def openai_api_key(self) -> str:
        """API key do OpenAI."""
        return self.require("openai-api-key")

    @property
    def redis_url(self) -> str:
        """URL do Redis."""
        return self.require("redis-url")

    @property
    def whatsapp_access_token(self) -> str:
        """Token de acesso do WhatsApp."""
        return self.require("whatsapp-access-token")

    @property
    def whatsapp_verify_token(self) -> str:
        """Token de verificação do webhook."""
        return self.require("whatsapp-verify-token")

    @property
    def whatsapp_webhook_secret(self) -> str:
        """Secret do webhook."""
        return self.require("whatsapp-webhook-secret")
