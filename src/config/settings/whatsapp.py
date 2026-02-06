"""Settings específicas de WhatsApp.

Configurações do canal WhatsApp via Graph API.
Cada canal deve ter seu próprio arquivo de settings para isolamento.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

# Constantes do Graph API
GRAPH_API_VERSION: str = "v24.0"
GRAPH_API_BASE_URL: str = "https://graph.facebook.com"


@dataclass(frozen=True)
class WhatsAppSettings:
    """Configurações do canal WhatsApp.

    Attributes:
        verify_token: Token para verificação de webhook
        webhook_secret: Secret para validação HMAC de payloads
        access_token: Token de acesso à Graph API
        phone_number_id: ID do número de telefone no Meta Business
        business_account_id: ID da conta de negócios (WABA)
        api_version: Versão da Graph API (ex: v24.0)
        api_base_url: URL base da Graph API
        request_timeout_seconds: Timeout para requisições HTTP
        max_retries: Máximo de tentativas em caso de erro
        circuit_breaker_threshold: Limiar para abrir circuit breaker
        circuit_breaker_reset_seconds: Tempo para reset do circuit breaker
        webhook_processing_mode: Modo de processamento do webhook (async|inline)
    """

    # Credenciais (carregadas de env ou Secret Manager)
    verify_token: str = ""
    webhook_secret: str = ""
    access_token: str = ""
    phone_number_id: str = ""
    business_account_id: str = ""

    # API
    api_version: str = GRAPH_API_VERSION
    api_base_url: str = GRAPH_API_BASE_URL

    # Timeouts e retries
    request_timeout_seconds: float = 30.0
    max_retries: int = 3

    # Circuit breaker
    circuit_breaker_threshold: int = 5
    circuit_breaker_reset_seconds: int = 60

    # Webhook processing
    webhook_processing_mode: str = "async"

    # Media upload
    media_upload_timeout_seconds: float = 120.0
    media_max_size_bytes: int = 16 * 1024 * 1024  # 16MB

    @property
    def api_endpoint(self) -> str:
        """URL base completa da API com versão."""
        return f"{self.api_base_url}/{self.api_version}"

    def get_messages_endpoint(self, phone_number_id: str | None = None) -> str:
        """Retorna URL para envio de mensagens.

        Args:
            phone_number_id: ID do número. Usa self.phone_number_id se None.

        Returns:
            URL completa no formato: https://graph.facebook.com/v24.0/{id}/messages

        Raises:
            ValueError: Se phone_number_id não informado e não configurado.
        """
        pid = phone_number_id or self.phone_number_id
        if not pid:
            raise ValueError("phone_number_id é obrigatório")
        return f"{self.api_endpoint}/{pid}/messages"

    def get_media_endpoint(self, phone_number_id: str | None = None) -> str:
        """Retorna URL para upload de mídia.

        Args:
            phone_number_id: ID do número. Usa self.phone_number_id se None.

        Returns:
            URL completa no formato: https://graph.facebook.com/v24.0/{id}/media
        """
        pid = phone_number_id or self.phone_number_id
        if not pid:
            raise ValueError("phone_number_id é obrigatório")
        return f"{self.api_endpoint}/{pid}/media"

    def validate(self) -> list[str]:
        """Valida configurações mínimas de WhatsApp.

        Returns:
            Lista de erros de validação (vazia = tudo OK).
        """
        errors: list[str] = []

        if not self.phone_number_id:
            errors.append("WHATSAPP_PHONE_NUMBER_ID não configurado")

        if not self.access_token:
            errors.append("WHATSAPP_ACCESS_TOKEN não configurado")

        if self.request_timeout_seconds <= 0:
            errors.append("WHATSAPP_REQUEST_TIMEOUT_SECONDS deve ser > 0")

        if self.max_retries < 0:
            errors.append("WHATSAPP_MAX_RETRIES deve ser >= 0")

        if self.webhook_processing_mode not in ("async", "inline"):
            errors.append(
                "WHATSAPP_WEBHOOK_PROCESSING_MODE deve ser 'async' ou 'inline'"
            )

        return errors


def _load_from_env() -> WhatsAppSettings:
    """Carrega WhatsAppSettings a partir de variáveis de ambiente."""
    environment = os.getenv("ENVIRONMENT", "").lower()
    default_processing_mode = (
        "inline" if environment in ("staging", "development", "dev", "test") else "async"
    )
    return WhatsAppSettings(
        verify_token=os.getenv("WHATSAPP_VERIFY_TOKEN", ""),
        webhook_secret=os.getenv("WHATSAPP_WEBHOOK_SECRET", ""),
        access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
        phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
        business_account_id=os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", ""),
        api_version=os.getenv("WHATSAPP_API_VERSION", GRAPH_API_VERSION),
        api_base_url=os.getenv("WHATSAPP_API_BASE_URL", GRAPH_API_BASE_URL),
        request_timeout_seconds=float(
            os.getenv("WHATSAPP_REQUEST_TIMEOUT_SECONDS", "30")
        ),
        max_retries=int(os.getenv("WHATSAPP_MAX_RETRIES", "3")),
        circuit_breaker_threshold=int(
            os.getenv("WHATSAPP_CIRCUIT_BREAKER_THRESHOLD", "5")
        ),
        circuit_breaker_reset_seconds=int(
            os.getenv("WHATSAPP_CIRCUIT_BREAKER_RESET_SECONDS", "60")
        ),
        media_upload_timeout_seconds=float(
            os.getenv("WHATSAPP_MEDIA_UPLOAD_TIMEOUT_SECONDS", "120")
        ),
        media_max_size_bytes=int(
            os.getenv("WHATSAPP_MEDIA_MAX_SIZE_BYTES", str(16 * 1024 * 1024))
        ),
        webhook_processing_mode=os.getenv(
            "WHATSAPP_WEBHOOK_PROCESSING_MODE", default_processing_mode
        ).lower(),
    )


@lru_cache(maxsize=1)
def get_whatsapp_settings() -> WhatsAppSettings:
    """Retorna instância cacheada de WhatsAppSettings.

    A cache garante singleton para múltiplas injeções.
    """
    return _load_from_env()
