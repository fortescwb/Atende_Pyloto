"""Extrator de payloads Telegram Bot API.

Estrutura do webhook Telegram:
- update_id
- message (ou edited_message, channel_post, callback_query, etc.)

Campos típicos de message:
- message_id, from, chat, date, text, photo, video, audio, document

TODO: Implementar quando canal Telegram for ativado.
"""

from __future__ import annotations

from typing import Any


def extract_payload_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai mensagens do payload Telegram para estrutura intermediária.

    TODO: Implementar extração específica Telegram.
    """
    _ = payload  # Placeholder
    return []
