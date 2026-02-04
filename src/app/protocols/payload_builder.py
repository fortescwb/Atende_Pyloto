"""Protocolos de construção de payload outbound."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .models import OutboundMessageRequest


class PayloadBuilderProtocol(Protocol):
    """Contrato mínimo para construir payloads de envio."""

    def build_full_payload(self, request: OutboundMessageRequest) -> dict: ...
