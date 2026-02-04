"""Extrator de payloads Google Calendar API.

Google Calendar usa push notifications via webhook.
Estrutura típica:
- X-Goog-Resource-State header (sync, exists, not_exists)
- events.list() para obter detalhes

Campos típicos de evento:
- id, summary, description, start, end, attendees, status

TODO: Implementar quando canal Google Calendar for ativado.
"""

from __future__ import annotations

from typing import Any


def extract_calendar_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai eventos do payload Google Calendar para estrutura intermediária.

    TODO: Implementar extração específica Google Calendar.
    """
    _ = payload  # Placeholder
    return []
