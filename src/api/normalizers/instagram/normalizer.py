"""Normalizer Instagram — converte payloads para modelo interno.

TODO: Implementar quando canal Instagram for ativado.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.protocols.models import NormalizedMessage


def normalize_messages(payload: dict[str, Any]) -> list[NormalizedMessage]:
    """Normaliza mensagens Instagram para modelo interno.

    TODO: Implementar normalização específica Instagram.
    """
    _ = payload  # Placeholder
    return []
