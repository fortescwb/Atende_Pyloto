"""Disponibilidade de datas/horarios para Flow de agendamento."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.protocols.calendar_service import CalendarServiceProtocol

_PT_WEEKDAY = ("Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom")
_PT_MONTH = (
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
)


def get_available_dates(
    *,
    days_ahead: int = 14,
    now: datetime | None = None,
    calendar_service: CalendarServiceProtocol | None = None,
) -> list[dict[str, object]]:
    """Retorna proximas datas uteis para reuniao."""
    dates = _build_date_options(days_ahead=days_ahead, now=now)
    if calendar_service is None:
        return dates
    return _run_async_or_fallback(
        async_call=lambda: get_available_dates_async(
            days_ahead=days_ahead,
            now=now,
            calendar_service=calendar_service,
        ),
        fallback=dates,
    )


async def get_available_dates_async(
    *,
    days_ahead: int = 14,
    now: datetime | None = None,
    calendar_service: CalendarServiceProtocol,
) -> list[dict[str, object]]:
    """Consulta disponibilidade real por data via servico de calendario."""
    dates = _build_date_options(days_ahead=days_ahead, now=now)
    if not dates:
        return []
    slot_batches = await asyncio.gather(
        *(calendar_service.check_availability(str(item["id"])) for item in dates)
    )
    for item, slots in zip(dates, slot_batches, strict=False):
        item["enabled"] = any(slot.available for slot in slots)
    return dates


def get_available_times(
    *,
    start_hour: int = 9,
    end_hour: int = 17,
    date: str | None = None,
    calendar_service: CalendarServiceProtocol | None = None,
) -> list[dict[str, object]]:
    """Retorna horarios no intervalo comercial.

    `end_hour` e exclusivo: 9-17 gera 09:00 ate 16:00.
    """
    times = _build_time_options(start_hour=start_hour, end_hour=end_hour)
    if calendar_service is None or not date:
        return times
    return _run_async_or_fallback(
        async_call=lambda: get_available_times_async(
            date=date,
            calendar_service=calendar_service,
            start_hour=start_hour,
            end_hour=end_hour,
        ),
        fallback=times,
    )


async def get_available_times_async(
    *,
    date: str,
    calendar_service: CalendarServiceProtocol,
    start_hour: int = 9,
    end_hour: int = 17,
) -> list[dict[str, object]]:
    """Retorna apenas horarios com slot disponivel na data informada."""
    if end_hour <= start_hour:
        return []
    slots = await calendar_service.check_availability(
        date,
        start_hour=start_hour,
        end_hour=end_hour,
    )
    available_times = sorted(
        {
            slot.start.strftime("%H:%M")
            for slot in slots
            if slot.available and start_hour <= slot.start.hour < end_hour
        }
    )
    return [{"id": value, "title": value, "enabled": True} for value in available_times]


def _build_date_options(*, days_ahead: int, now: datetime | None) -> list[dict[str, object]]:
    if days_ahead <= 0:
        return []
    base = now or datetime.now(tz=UTC)
    dates: list[dict[str, object]] = []
    for step in range(1, days_ahead + 1):
        candidate = base + timedelta(days=step)
        if candidate.weekday() >= 5:
            continue
        weekday = _PT_WEEKDAY[candidate.weekday()]
        month = _PT_MONTH[candidate.month - 1]
        dates.append(
            {
                "id": candidate.strftime("%Y-%m-%d"),
                "title": f"{weekday}, {candidate.day:02d} de {month}",
                "enabled": True,
            }
        )
    return dates


def _build_time_options(*, start_hour: int, end_hour: int) -> list[dict[str, object]]:
    if end_hour <= start_hour:
        return []
    return [
        {"id": f"{hour:02d}:00", "title": f"{hour:02d}:00", "enabled": True}
        for hour in range(start_hour, end_hour)
    ]


def _run_async_or_fallback(
    *,
    async_call: Any,
    fallback: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Mantem API sync sem quebrar chamadas em contexto com loop ativo."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(async_call())
    return fallback
