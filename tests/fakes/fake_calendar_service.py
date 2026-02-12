"""Fake in-memory de calendario para testes deterministas."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.appointment import AppointmentData, CalendarEvent, TimeSlot


class FakeCalendarService:
    """Implementa o protocolo sem IO para testes unitarios.

    Mantemos estado local para validar fluxos de criacao e cancelamento
    sem depender de APIs externas.
    """

    def __init__(self, predefined_slots: list[TimeSlot] | None = None) -> None:
        self._slots = predefined_slots or _build_default_slots()
        self._events: dict[str, CalendarEvent] = {}

    async def check_availability(
        self,
        date: str,
        *,
        start_hour: int = 9,
        end_hour: int = 17,
    ) -> list[TimeSlot]:
        _ = (date, start_hour, end_hour)
        return [slot.model_copy(deep=True) for slot in self._slots]

    async def create_event(self, appointment: AppointmentData) -> CalendarEvent:
        event_id = uuid4().hex[:12]
        start = _parse_start_datetime(appointment.date, appointment.time)
        event = CalendarEvent(
            event_id=event_id,
            html_link=f"https://calendar.google.com/fake/{event_id}",
            start=start,
            end=start + timedelta(minutes=appointment.duration_min),
            status="confirmed",
        )
        self._events[event_id] = event
        return event.model_copy(deep=True)

    async def cancel_event(self, event_id: str) -> bool:
        event = self._events.pop(event_id, None)
        return event is not None

    async def get_event(self, event_id: str) -> CalendarEvent | None:
        event = self._events.get(event_id)
        return event.model_copy(deep=True) if event is not None else None


def _build_default_slots() -> list[TimeSlot]:
    """Usa um conjunto fixo para manter os testes previsiveis."""
    start = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)
    return [
        TimeSlot(start=start, end=start + timedelta(minutes=30), available=True),
        TimeSlot(
            start=start + timedelta(hours=1),
            end=start + timedelta(hours=1, minutes=30),
            available=True,
        ),
        TimeSlot(
            start=start + timedelta(hours=2),
            end=start + timedelta(hours=2, minutes=30),
            available=False,
        ),
    ]


def _parse_start_datetime(date_value: str, time_value: str) -> datetime:
    """Gera datetime consistente para o evento fake.

    Em caso de entrada invalida, retornamos um valor fixo para nao tornar
    o teste dependente do relogio da maquina.
    """
    try:
        start = datetime.fromisoformat(f"{date_value}T{time_value}:00")
    except ValueError:
        return datetime(2026, 1, 15, 9, 0, tzinfo=UTC)
    return start if start.tzinfo is not None else start.replace(tzinfo=UTC)
