"""Adapters concretos para WhatsApp (wiring em app/bootstrap).

Este módulo é o único autorizado a acoplar app <-> api.
"""

from __future__ import annotations

import logging
from typing import Any

from api.connectors.whatsapp.http_client import WhatsAppHttpClient
from api.normalizers.whatsapp.normalizer import normalize_messages
from api.payload_builders.whatsapp.factory import build_full_payload
from api.validators.whatsapp.errors import ValidationError as ApiValidationError
from api.validators.whatsapp.validator_dispatcher import WhatsAppMessageValidator
from app.protocols.models import NormalizedMessage, OutboundMessageRequest, OutboundMessageResponse
from app.protocols.normalizer import MessageNormalizerProtocol
from app.protocols.outbound_sender import OutboundSenderProtocol
from app.protocols.payload_builder import PayloadBuilderProtocol
from app.protocols.validator import OutboundRequestValidatorProtocol, ValidationError
from config.settings import get_whatsapp_settings

logger = logging.getLogger(__name__)


class GraphApiNormalizer(MessageNormalizerProtocol):
    """Normalizador baseado em Graph API."""

    def normalize(self, payload: dict[str, Any]) -> list[NormalizedMessage]:
        return normalize_messages(payload)


class GraphApiPayloadBuilder(PayloadBuilderProtocol):
    """Builder de payload para Graph API."""

    def build_full_payload(self, request: OutboundMessageRequest) -> dict:
        return build_full_payload(request)


class GraphApiOutboundValidator(OutboundRequestValidatorProtocol):
    """Validador outbound usando regras do Graph API."""

    def __init__(self) -> None:
        self._validator = WhatsAppMessageValidator()

    def validate_outbound_request(self, request: OutboundMessageRequest) -> None:
        try:
            self._validator.validate_outbound_request(request)
        except ApiValidationError as exc:
            raise ValidationError(str(exc)) from exc


class GraphApiOutboundSender(OutboundSenderProtocol):
    """Sender outbound usando cliente HTTP WhatsApp."""

    async def send(
        self,
        request: OutboundMessageRequest,
        payload: dict[str, Any],
    ) -> OutboundMessageResponse:
        whatsapp = get_whatsapp_settings()

        phone_id = whatsapp.phone_number_id
        api_version = whatsapp.api_version
        base_url = whatsapp.api_base_url
        endpoint = f"{base_url}/{api_version}/{phone_id}/messages"

        try:
            http_client = WhatsAppHttpClient()
            response = await http_client.send_message(
                endpoint=endpoint,
                access_token=whatsapp.access_token,
                payload=payload,
            )

            message_id = response.get("messages", [{}])[0].get("id", "unknown")
            logger.info(
                "message_sent_to_whatsapp_api",
                extra={
                    "message_id": message_id,
                    "request_id": request.idempotency_key,
                },
            )

            return OutboundMessageResponse(
                success=True,
                message_id=message_id,
            )

        except Exception as exc:
            logger.error(
                "whatsapp_send_failed",
                extra={
                    "error": str(exc),
                    "request_id": request.idempotency_key,
                },
            )
            return OutboundMessageResponse(
                success=False,
                error_code="WHATSAPP_API_ERROR",
                error_message=str(exc),
            )
