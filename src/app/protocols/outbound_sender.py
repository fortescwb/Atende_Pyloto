"""Protocolos de envio outbound."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from .models import OutboundMessageRequest, OutboundMessageResponse


class OutboundSenderProtocol(Protocol):
    """Contrato mínimo para enviar payload outbound."""

    async def send(
        self,
        request: OutboundMessageRequest,
        payload: dict[str, Any],
    ) -> OutboundMessageResponse: ...
