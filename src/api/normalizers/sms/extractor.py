"""Extrator de payloads SMS (Twilio/Vonage).

Estrutura típica (Twilio webhook):
- MessageSid, From, To, Body, NumMedia, MediaUrl0, etc.

Estrutura Vonage:
- msisdn, to, messageId, text, type

TODO: Implementar quando canal SMS for ativado.
"""

from __future__ import annotations

from typing import Any


def extract_payload_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai SMS do payload para estrutura intermediária.

    TODO: Implementar extração específica SMS.
    """
    _ = payload  # Placeholder
    return []
