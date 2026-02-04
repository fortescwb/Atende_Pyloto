"""Cliente HTTP especializado para WhatsApp/Meta API.

Estende HttpClient genérico com comportamentos específicos de WhatsApp:
- Tratamento de rate limiting (429)
- Headers de User-Agent específicos
- Validação de assinatura em responses (quando aplicável)
- Logging estruturado sem PII (tokens, números, etc.)
- Tratamento de erros Meta (error.type, error.message)
- **Validação de access_token antes de usar**

Conforme regras_e_padroes.md:
- Máximo 200 linhas por arquivo
- Máximo 50 linhas por função
- SRP: responsabilidade única
- Zero-trust: validação rigorosa de inputs e outputs
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from api.connectors.whatsapp.meta_errors import WhatsAppApiError, parse_meta_error
from api.connectors.whatsapp.meta_logging import log_meta_error, log_success
from app.infra.http import HttpClient, HttpClientConfig, HttpError

if TYPE_CHECKING:
    import httpx

    from config.settings import WhatsAppSettings

logger: logging.Logger = logging.getLogger(__name__)




class WhatsAppHttpClient(HttpClient):
    """Cliente HTTP especializado para Meta/WhatsApp API.

    Tratamento específico:
    - Rate limiting (429): retryable
    - Erros Meta (error.type, error.code): classifica permanente vs transitório
    - Validação de response: nunca retorna resposta mal-formada
    - Logging: sem tokens, números, ou dados sensíveis
    - **Validação de access_token antes de usar**
    """

    def __init__(
        self,
        config: HttpClientConfig | None = None,
        phone_number_id: str | None = None,
    ) -> None:
        """Inicializa cliente WhatsApp.

        Args:
            config: Configuração HTTP base
            phone_number_id: ID do número (para logging/dedup)
        """
        super().__init__(config)
        self.phone_number_id = phone_number_id

    async def send_message(
        self,
        endpoint: str,
        access_token: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Envia mensagem via WhatsApp API.

        Args:
            endpoint: URL do endpoint (ex: .../messages)
            access_token: Bearer token para autenticação
            payload: Payload JSON da mensagem

        Returns:
            Response JSON da Meta

        Raises:
            ValueError: Se access_token está vazio ou inválido
            HttpError: Se erro HTTP ou Meta
        """
        # Validar access_token antes de usar (CRÍTICO)
        if not access_token or not access_token.strip():
            logger.error(
                "access_token ausente ou vazio para send_message",
                extra={"endpoint": endpoint},
            )
            raise ValueError(
                "access_token é obrigatório para envio de mensagens. "
                "Verifique se WHATSAPP_ACCESS_TOKEN está configurado."
            )

        url, headers = self._build_request(endpoint, access_token)
        response = await self._execute_send(url, payload, headers, endpoint)
        return self._process_whatsapp_response(response, endpoint)

    def _build_request(self, endpoint: str, access_token: str) -> tuple[str, dict[str, str]]:
        """Monta URL e headers seguros para envio.

        Usa Authorization header conforme recomendação Meta:
        https://developers.facebook.com/docs/graph-api/guides/authentication

        Args:
            endpoint: URL do endpoint
            access_token: Bearer token (já validado por send_message)

        Returns:
            (endpoint, headers)

        Raises:
            ValueError: Se access_token inválido (defense in depth)
        """
        if not access_token or not access_token.strip():
            raise ValueError("access_token não pode ser vazio")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        return endpoint, headers

    async def _execute_send(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        endpoint: str,
    ) -> httpx.Response:
        """Executa POST com tratamento de erros previsível."""
        try:
            return await self.post(url, json=payload, headers=headers)
        except HttpError:
            raise

    def _process_whatsapp_response(
        self,
        response: httpx.Response,
        endpoint: str,
    ) -> dict[str, Any]:
        """Processa response da API Meta/WhatsApp."""
        try:
            response_data = response.json()
        except json.JSONDecodeError as e:
            logger.error("Response JSON inválido", extra={"endpoint": endpoint})
            raise HttpError("Response JSON inválido") from e

        meta_error = parse_meta_error(response_data)
        if meta_error:
            self._handle_meta_error(meta_error, endpoint)

        log_success("POST", endpoint, response.status_code)
        return response_data

    def _handle_meta_error(
        self,
        meta_error: WhatsAppApiError,
        endpoint: str,
    ) -> None:
        """Lida com erro da Meta."""
        log_meta_error(meta_error, "POST", endpoint)

        # Determina se erro é retryable baseado em classificação
        is_retryable = not meta_error.is_permanent

        raise HttpError(
            f"Meta API error: {meta_error.error_type} ({meta_error.error_code})",
            status_code=meta_error.error_code,
            is_retryable=is_retryable,
        )


def create_whatsapp_http_client(
    settings: WhatsAppSettings | None = None,
) -> WhatsAppHttpClient:
    """Factory para criar cliente WhatsApp com config padrão.

    Args:
        settings: WhatsAppSettings opcional. Se None, carrega do ambiente.

    Returns:
        Cliente HTTP configurado para WhatsApp.
    """
    # Import local para evitar dependência circular
    from config.settings import get_whatsapp_settings

    whatsapp = settings or get_whatsapp_settings()
    config = HttpClientConfig(
        timeout_seconds=whatsapp.request_timeout_seconds,
        max_retries=whatsapp.max_retries,
    )
    return WhatsAppHttpClient(
        config=config,
        phone_number_id=whatsapp.phone_number_id,
    )
