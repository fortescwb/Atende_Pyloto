"""Disponibilidade de datas/horários para Flow de agendamento."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
) -> list[dict[str, object]]:
    """Retorna próximas datas úteis para reunião."""
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


def get_available_times(
    *,
    start_hour: int = 9,
    end_hour: int = 17,
) -> list[dict[str, object]]:
    """Retorna horários disponíveis no intervalo comercial.

    `end_hour` é exclusivo: 9-17 gera 09:00 até 16:00.
    """
    if end_hour <= start_hour:
        return []
    times: list[dict[str, object]] = []
    for hour in range(start_hour, end_hour):
        times.append({"id": f"{hour:02d}:00", "title": f"{hour:02d}:00", "enabled": True})
    return times
