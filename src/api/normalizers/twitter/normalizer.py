"""Normalizer Twitter/X — converte payloads para modelo interno.

TODO: Implementar quando canal Twitter/X for ativado.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.protocols.models import NormalizedMessage


def normalize_messages(payload: dict[str, Any]) -> list[NormalizedMessage]:
    """Normaliza mensagens Twitter/X para modelo interno.

    TODO: Implementar normalização específica Twitter/X.
    """
    _ = payload  # Placeholder
    return []
