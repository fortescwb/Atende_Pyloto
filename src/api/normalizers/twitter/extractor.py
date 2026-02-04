"""Extrator de payloads Twitter/X API v2.

Estrutura do webhook (Account Activity API):
- for_user_id
- direct_message_events, tweet_create_events, etc.

Campos típicos de DM:
- id, created_timestamp, message_create.message_data.text

TODO: Implementar quando canal Twitter/X for ativado.
"""

from __future__ import annotations

from typing import Any


def extract_payload_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai mensagens do payload Twitter/X para estrutura intermediária.

    TODO: Implementar extração específica Twitter/X.
    """
    _ = payload  # Placeholder
    return []
