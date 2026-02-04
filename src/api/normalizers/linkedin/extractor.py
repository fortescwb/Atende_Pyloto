"""Extrator de payloads LinkedIn API.

Estrutura do webhook LinkedIn:
- Eventos de mensagem via LinkedIn Messaging API
- Notificações de comentários via LinkedIn Marketing API

TODO: Implementar quando canal LinkedIn for ativado.
"""

from __future__ import annotations

from typing import Any


def extract_payload_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai mensagens do payload LinkedIn para estrutura intermediária.

    TODO: Implementar extração específica LinkedIn.
    """
    _ = payload  # Placeholder
    return []
