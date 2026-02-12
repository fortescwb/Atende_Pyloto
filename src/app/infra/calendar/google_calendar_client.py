"""Client concreto de Google Calendar para o dominio de agendamentos."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.infra.calendar.google_calendar_parsers import (
    extract_free_slots,
    http_status,
    map_calendar_event,
)
from app.observability import get_correlation_id
from app.protocols.calendar_service import CalendarServiceProtocol

if TYPE_CHECKING:
    from app.domain.appointment import AppointmentData, CalendarEvent, TimeSlot

logger = logging.getLogger(__name__)

_COMPONENT = "google_calendar_client"
_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"


class GoogleCalendarClient(CalendarServiceProtocol):
    """Implementacao do protocolo de calendario usando API v3 do Google."""

    __slots__ = ("_calendar_id", "_service", "_timezone", "_zone")

    def __init__(self, *, calendar_id: str, credentials_json: str, timezone: str) -> None:
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(credentials_json),
            scopes=[_CALENDAR_SCOPE],
        )
        self._calendar_id = calendar_id
        self._timezone = timezone
        self._zone = ZoneInfo(timezone)
        self._service = build("calendar", "v3", credentials=credentials, cache_discovery=False)

    async def check_availability(
        self,
        date: str,
        *,
        start_hour: int = 9,
        end_hour: int = 17,
    ) -> list[TimeSlot]:
        if start_hour >= end_hour:
            return []
        try:
            day = datetime.fromisoformat(date).date()
            start_dt = datetime.combine(day, time(hour=start_hour), tzinfo=self._zone)
            end_dt = datetime.combine(day, time(hour=end_hour), tzinfo=self._zone)
            body = {
                "timeMin": start_dt.isoformat(),
                "timeMax": end_dt.isoformat(),
                "timeZone": self._timezone,
                "items": [{"id": self._calendar_id}],
            }
            response = await asyncio.to_thread(self._query_freebusy_sync, body)
            return extract_free_slots(response, self._calendar_id, start_dt, end_dt, self._zone)
        except HttpError as exc:
            self._log_error(action="check_availability", result="error", exc=exc)
            return []
        except Exception:
            self._log_error(action="check_availability", result="error")
            return []

    async def create_event(self, appointment: AppointmentData) -> CalendarEvent:
        try:
            start_dt = datetime.fromisoformat(f"{appointment.date}T{appointment.time}").replace(
                tzinfo=self._zone
            )
            end_dt = start_dt + timedelta(minutes=appointment.duration_min)
            body: dict[str, Any] = {
                # Mantemos resumo neutro para reduzir exposicao desnecessaria de PII no convite.
                "summary": f"Atendimento {appointment.vertical or 'Pyloto'}".strip(),
                "description": appointment.description,
                "start": {"dateTime": start_dt.isoformat(), "timeZone": self._timezone},
                "end": {"dateTime": end_dt.isoformat(), "timeZone": self._timezone},
                "attendees": [{"email": appointment.attendee_email}],
            }
            include_conference = appointment.meeting_mode == "online"
            if include_conference:
                body["conferenceData"] = {
                    "createRequest": {
                        "requestId": uuid4().hex,
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                }
            response = await asyncio.to_thread(self._insert_event_sync, body, include_conference)
            return map_calendar_event(response, self._zone)
        except HttpError as exc:
            self._log_error(action="create_event", result="error", exc=exc)
            raise
        except Exception:
            self._log_error(action="create_event", result="error")
            raise

    async def cancel_event(self, event_id: str) -> bool:
        try:
            await asyncio.to_thread(self._delete_event_sync, event_id)
            return True
        except HttpError as exc:
            status_code = http_status(exc)
            if status_code in {404, 410}:
                logger.info(
                    "google_calendar_event_missing",
                    extra={
                        "component": _COMPONENT,
                        "action": "cancel_event",
                        "result": "not_found",
                        "correlation_id": get_correlation_id(),
                    },
                )
                return False
            self._log_error(action="cancel_event", result="error", exc=exc)
            raise
        except Exception:
            self._log_error(action="cancel_event", result="error")
            raise

    async def get_event(self, event_id: str) -> CalendarEvent | None:
        try:
            response = await asyncio.to_thread(self._get_event_sync, event_id)
            return map_calendar_event(response, self._zone)
        except HttpError as exc:
            if http_status(exc) == 404:
                return None
            self._log_error(action="get_event", result="error", exc=exc)
            raise
        except Exception:
            self._log_error(action="get_event", result="error")
            raise

    def _query_freebusy_sync(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._service.freebusy().query(body=body).execute()

    def _insert_event_sync(self, body: dict[str, Any], include_conference: bool) -> dict[str, Any]:
        events = self._service.events()
        if include_conference:
            return events.insert(
                calendarId=self._calendar_id,
                body=body,
                sendUpdates="all",
                conferenceDataVersion=1,
            ).execute()
        return events.insert(calendarId=self._calendar_id, body=body, sendUpdates="all").execute()

    def _delete_event_sync(self, event_id: str) -> None:
        self._service.events().delete(
            calendarId=self._calendar_id,
            eventId=event_id,
            sendUpdates="all",
        ).execute()

    def _get_event_sync(self, event_id: str) -> dict[str, Any]:
        return self._service.events().get(calendarId=self._calendar_id, eventId=event_id).execute()

    def _log_error(self, *, action: str, result: str, exc: HttpError | None = None) -> None:
        extra = {
            "component": _COMPONENT,
            "action": action,
            "result": result,
            "correlation_id": get_correlation_id(),
        }
        if exc is not None:
            extra["status_code"] = http_status(exc)
            extra["error_type"] = type(exc).__name__
            logger.error("google_calendar_http_error", extra=extra)
            return
        logger.exception("google_calendar_unexpected_error", extra=extra)
