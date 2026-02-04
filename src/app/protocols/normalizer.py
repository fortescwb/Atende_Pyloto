"""Protocolos de normalização inbound."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from .models import NormalizedMessage


class MessageNormalizerProtocol(Protocol):
    """Contrato mínimo para normalização de payload inbound."""

    def normalize(self, payload: dict[str, Any]) -> list[NormalizedMessage]: ...
