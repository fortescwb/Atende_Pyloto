"""Extrator de payloads Instagram Messaging API.

Estrutura do webhook Instagram:
- entry[].messaging[] (diferente de WhatsApp que usa entry[].changes[])

Tipos de evento:
- message (text, attachments)
- story_reply
- story_mention
- postback
- referral
- echo

TODO: Implementar quando canal Instagram for ativado.
"""

from __future__ import annotations

from typing import Any


def extract_payload_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai mensagens do payload Instagram para estrutura intermediária.

    TODO: Implementar extração específica Instagram.
    """
    _ = payload  # Placeholder
    return []
