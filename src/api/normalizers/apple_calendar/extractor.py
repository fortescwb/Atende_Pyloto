"""Extrator de payloads Apple Calendar (CalDAV).

Apple Calendar não tem webhook nativo — usa CalDAV.
Estrutura típica (iCalendar/VEVENT):
- VEVENT com UID, SUMMARY, DTSTART, DTEND, ATTENDEE, STATUS

TODO: Implementar quando canal Apple Calendar for ativado.
"""

from __future__ import annotations

from typing import Any


def extract_calendar_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai eventos do payload CalDAV para estrutura intermediária.

    TODO: Implementar extração específica Apple Calendar.
    """
    _ = payload  # Placeholder
    return []
