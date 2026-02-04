"""Use case para envio outbound WhatsApp."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from app.protocols.models import OutboundMessageRequest, OutboundMessageResponse
from app.protocols.validator import OutboundRequestValidatorProtocol, ValidationError

if TYPE_CHECKING:
    from app.protocols.outbound_sender import OutboundSenderProtocol
    from app.protocols.payload_builder import PayloadBuilderProtocol


class SendOutboundMessageUseCase:
    """Orquestra validação, build e envio outbound."""

    def __init__(
        self,
        validator: OutboundRequestValidatorProtocol,
        builder: PayloadBuilderProtocol,
        sender: OutboundSenderProtocol,
    ) -> None:
        self._validator = validator
        self._builder = builder
        self._sender = sender

    async def execute(self, request: OutboundMessageRequest) -> OutboundMessageResponse:
        """Executa envio outbound com validação e tratamento de erro."""
        try:
            self._validator.validate_outbound_request(request)
        except ValidationError as exc:
            return OutboundMessageResponse(
                success=False,
                error_code="VALIDATION_ERROR",
                error_message=str(exc),
            )

        try:
            payload = self._builder.build_full_payload(request)
        except Exception as exc:
            return OutboundMessageResponse(
                success=False,
                error_code="PAYLOAD_BUILD_ERROR",
                error_message=str(exc),
            )

        return await self._sender.send(request, payload)

    @staticmethod
    def generate_dedupe_key(
        to: str,
        message_type: str,
        content_hash: str,
    ) -> str:
        """Gera chave de deduplicação baseada em conteúdo."""
        key_material = f"{to}:{message_type}:{content_hash}"
        return hashlib.sha256(key_material.encode()).hexdigest()

    @staticmethod
    def hash_content(payload: dict[str, Any]) -> str:
        """Gera hash determinístico do payload para dedupe."""
        raw = repr(sorted(payload.items()))
        return hashlib.sha256(raw.encode()).hexdigest()
