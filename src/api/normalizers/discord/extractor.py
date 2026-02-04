"""Extrator de payloads Discord Gateway API.

Estrutura do evento Discord:
- MESSAGE_CREATE, MESSAGE_UPDATE, MESSAGE_REACTION_ADD, etc.

Campos típicos:
- id, channel_id, author, content, attachments, embeds

TODO: Implementar quando canal Discord for ativado.
"""

from __future__ import annotations

from typing import Any


def extract_payload_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai mensagens do payload Discord para estrutura intermediária.

    TODO: Implementar extração específica Discord.
    """
    _ = payload  # Placeholder
    return []
