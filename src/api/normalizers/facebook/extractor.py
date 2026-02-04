"""Extrator de payloads Facebook Messenger API.

Estrutura do webhook Facebook:
- entry[].messaging[] (similar a Instagram)

Tipos de evento:
- message (text, attachments)
- postback
- referral
- optin
- delivery
- read
- echo
- account_linking

TODO: Implementar quando canal Facebook for ativado.
"""

from __future__ import annotations

from typing import Any


def extract_payload_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai mensagens do payload Facebook para estrutura intermediária.

    TODO: Implementar extração específica Facebook.
    """
    _ = payload  # Placeholder
    return []
