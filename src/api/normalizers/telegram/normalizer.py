"""Normalizer Telegram — converte payloads para modelo interno.

TODO: Implementar quando canal Telegram for ativado.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.protocols.models import NormalizedMessage


def normalize_messages(payload: dict[str, Any]) -> list[NormalizedMessage]:
    """Normaliza mensagens Telegram para modelo interno.

    TODO: Implementar normalização específica Telegram.
    """
    _ = payload  # Placeholder
    return []
