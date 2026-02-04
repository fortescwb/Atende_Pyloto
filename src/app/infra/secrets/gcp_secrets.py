"""GCP Secret Manager — integração com Google Cloud Secret Manager.

Provedor de secrets para staging/production.
Suporta cache em memória para evitar chamadas repetidas.

Referência: REGRAS_E_PADROES.md § 7 — Segurança
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from google.cloud.secretmanager import SecretManagerServiceClient

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_client() -> SecretManagerServiceClient:
    """Obtém cliente do Secret Manager (singleton via lru_cache)."""
    from google.cloud import secretmanager
    return secretmanager.SecretManagerServiceClient()


@lru_cache(maxsize=64)
def get_secret(
    secret_id: str,
    project_id: str | None = None,
    version: str = "latest",
) -> str:
    """Obtém valor de secret do GCP Secret Manager.

    Args:
        secret_id: ID do secret (ex.: openai-api-key-staging)
        project_id: ID do projeto GCP (default: env GCP_PROJECT)
        version: Versão do secret (default: latest)

    Returns:
        Valor do secret como string

    Raises:
        ValueError: Se project_id não fornecido e GCP_PROJECT não definido
        google.api_core.exceptions.NotFound: Se secret não existe
    """
    if project_id is None:
        project_id = os.getenv("GCP_PROJECT")
        if not project_id:
            msg = "GCP_PROJECT não definido e project_id não fornecido"
            raise ValueError(msg)

    client = _get_client()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"

    try:
        response = client.access_secret_version(request={"name": name})
        value = response.payload.data.decode("UTF-8")
        logger.debug("secret_loaded", extra={"secret_id": secret_id})
        return value
    except Exception as e:
        logger.error("secret_load_error", extra={"secret_id": secret_id, "error": str(e)})
        raise


async def get_secret_async(
    secret_id: str,
    project_id: str | None = None,
    version: str = "latest",
) -> str:
    """Obtém secret de forma assíncrona.

    Nota: Secret Manager Python SDK não tem async nativo.
    Esta implementação usa cache e é efetivamente síncrona.
    Para async real em alta escala, considere usar executor.

    Args:
        secret_id: ID do secret
        project_id: ID do projeto GCP
        version: Versão do secret

    Returns:
        Valor do secret
    """
    # TODO: Usar asyncio.to_thread para não bloquear
    return get_secret(secret_id, project_id, version)


class GCPSecretProvider:
    """Provedor de secrets usando GCP Secret Manager.

    Encapsula acesso a secrets com cache e fallback para env.

    Args:
        project_id: ID do projeto GCP
        environment: Ambiente (staging/production) para sufixo de secrets
    """

    def __init__(
        self,
        project_id: str | None = None,
        environment: str = "staging",
    ) -> None:
        self._project_id = project_id or os.getenv("GCP_PROJECT", "")
        self._environment = environment
        self._suffix = f"-{environment}" if environment else ""

    def get(self, key: str, default: str | None = None) -> str | None:
        """Obtém secret por nome.

        Tenta carregar do Secret Manager com sufixo de ambiente.
        Ex.: key="openai-api-key", environment="staging" -> "openai-api-key-staging"

        Args:
            key: Nome base do secret
            default: Valor padrão se não encontrado

        Returns:
            Valor do secret ou default
        """
        secret_id = f"{key}{self._suffix}"
        try:
            return get_secret(secret_id, self._project_id)
        except Exception as e:
            logger.warning(
                "secret_fallback_to_default",
                extra={"key": key, "secret_id": secret_id, "error": str(e)},
            )
            return default

    def require(self, key: str) -> str:
        """Obtém secret obrigatório.

        Args:
            key: Nome base do secret

        Returns:
            Valor do secret

        Raises:
            ValueError: Se secret não encontrado
        """
        value = self.get(key)
        if value is None:
            msg = f"Secret obrigatório não encontrado: {key}{self._suffix}"
            raise ValueError(msg)
        return value

    @property
    def openai_api_key(self) -> str:
        """API key do OpenAI."""
        return self.require("openai-api-key")

    @property
    def redis_url(self) -> str:
        """URL do Redis (Upstash)."""
        return self.require("redis-url")

    @property
    def whatsapp_access_token(self) -> str:
        """Token de acesso do WhatsApp."""
        return self.require("whatsapp-access-token")

    @property
    def whatsapp_verify_token(self) -> str:
        """Token de verificação do webhook WhatsApp."""
        return self.require("whatsapp-verify-token")

    @property
    def whatsapp_webhook_secret(self) -> str:
        """Secret para validação HMAC do webhook WhatsApp."""
        return self.require("whatsapp-webhook-secret")
