"""Normalizer Facebook — converte payloads para modelo interno.

TODO: Implementar quando canal Facebook for ativado.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.protocols.models import NormalizedMessage


def normalize_messages(payload: dict[str, Any]) -> list[NormalizedMessage]:
    """Normaliza mensagens Facebook para modelo interno.

    TODO: Implementar normalização específica Facebook.
    """
    _ = payload  # Placeholder
    return []
