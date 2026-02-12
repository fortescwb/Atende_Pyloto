"""Helpers internos de parsing para respostas da Google Calendar API."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.domain.appointment import CalendarEvent, TimeSlot

if TYPE_CHECKING:
    from zoneinfo import ZoneInfo

    from googleapiclient.errors import HttpError


def extract_free_slots(
    response: dict[str, Any],
    calendar_id: str,
    start_dt: datetime,
    end_dt: datetime,
    zone: ZoneInfo,
) -> list[TimeSlot]:
    calendars = response.get("calendars") if isinstance(response, dict) else {}
    calendar_data = calendars.get(calendar_id, {}) if isinstance(calendars, dict) else {}
    busy = calendar_data.get("busy", []) if isinstance(calendar_data, dict) else []
    ranges = sorted(
        (
            start,
            end,
        )
        for item in busy if isinstance(item, dict)
        if (start := parse_google_datetime(item.get("start"), zone))
        if (end := parse_google_datetime(item.get("end"), zone))
        if end > start
    )
    free_slots: list[TimeSlot] = []
    cursor = start_dt
    for busy_start, busy_end in ranges:
        if busy_start > cursor:
            free_slots.append(TimeSlot(start=cursor, end=busy_start, available=True))
        if busy_end > cursor:
            cursor = busy_end
    if cursor < end_dt:
        free_slots.append(TimeSlot(start=cursor, end=end_dt, available=True))
    return free_slots


def map_calendar_event(payload: dict[str, Any], zone: ZoneInfo) -> CalendarEvent:
    return CalendarEvent(
        event_id=str(payload.get("id") or ""),
        html_link=str(payload.get("htmlLink") or ""),
        start=_extract_event_datetime(payload.get("start"), zone),
        end=_extract_event_datetime(payload.get("end"), zone),
        status=str(payload.get("status") or ""),
    )


def parse_google_datetime(value: Any, zone: ZoneInfo) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=zone) if parsed.tzinfo is None else parsed.astimezone(zone)


def http_status(exc: HttpError) -> int | None:
    response = getattr(exc, "resp", None)
    return int(response.status) if response and getattr(response, "status", None) else None


def _extract_event_datetime(value: Any, zone: ZoneInfo) -> datetime:
    if isinstance(value, dict):
        if parsed := parse_google_datetime(value.get("dateTime"), zone):
            return parsed
        if isinstance(value.get("date"), str):
            return datetime.fromisoformat(value["date"]).replace(tzinfo=zone)
    # Falhamos explicitamente para evitar mapear evento invalido como horario falso.
    raise ValueError("missing_event_datetime")
