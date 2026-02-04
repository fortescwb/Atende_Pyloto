"""Protocolos de validação de payload outbound."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .models import OutboundMessageRequest


class ValidationError(Exception):
    """Erro de validação de payload."""


class OutboundRequestValidatorProtocol(Protocol):
    """Contrato mínimo para validação de requisições outbound."""

    def validate_outbound_request(self, request: OutboundMessageRequest) -> None: ...
