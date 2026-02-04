"""Sanitização comum para payloads Meta Graph API.

Responsabilidades:
- Remover/mascarar campos sensíveis
- Normalizar estrutura base
- Preparar payload para processamento seguro
"""

from __future__ import annotations

from typing import Any


def sanitize_message_payload(message: dict[str, Any]) -> dict[str, Any]:
    """Sanitiza payload intermediário sem alterar comportamento atual.

    Args:
        message: Payload extraído do webhook

    Returns:
        Payload sanitizado
    """
    if not isinstance(message, dict):
        return {}
    return message
