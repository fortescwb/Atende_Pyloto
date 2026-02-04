"""Normalizer Google Calendar — converte payloads para modelo interno.

TODO: Implementar quando canal Google Calendar for ativado.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.protocols.models import NormalizedMessage


def normalize_events(payload: dict[str, Any]) -> list[NormalizedMessage]:
    """Normaliza eventos Google Calendar para modelo interno.

    TODO: Implementar normalização específica Google Calendar.
    """
    _ = payload  # Placeholder
    return []
