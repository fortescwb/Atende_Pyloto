"""Extrator de payloads YouTube Data API.

YouTube não tem webhook nativo — usa polling ou Pub/Sub.
Estrutura típica:
- commentThreads.list() response
- comments.list() response

TODO: Implementar quando canal YouTube for ativado.
"""

from __future__ import annotations

from typing import Any


def extract_payload_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai comentários do payload YouTube para estrutura intermediária.

    TODO: Implementar extração específica YouTube.
    """
    _ = payload  # Placeholder
    return []
