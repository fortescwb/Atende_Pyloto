"""Extrator de payloads TikTok for Business API.

Estrutura do webhook TikTok:
- Notificações de comentários
- Mensagens diretas (quando disponível)

TODO: Implementar quando canal TikTok for ativado.
"""

from __future__ import annotations

from typing import Any


def extract_payload_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai mensagens do payload TikTok para estrutura intermediária.

    TODO: Implementar extração específica TikTok.
    """
    _ = payload  # Placeholder
    return []
