"""Testes do serviço de disponibilidade de agendamento."""

from __future__ import annotations

from datetime import UTC, datetime

from app.services.appointment_availability import get_available_dates, get_available_times


def test_get_available_dates_skips_weekends() -> None:
    # Segunda-feira, 2026-02-09
    now = datetime(2026, 2, 9, 12, 0, tzinfo=UTC)
    dates = get_available_dates(days_ahead=7, now=now)
    ids = [item["id"] for item in dates]

    assert "2026-02-14" not in ids  # sábado
    assert "2026-02-15" not in ids  # domingo
    assert ids[0] == "2026-02-10"


def test_get_available_times_default_business_hours() -> None:
    times = get_available_times()
    assert times[0]["id"] == "09:00"
    assert times[-1]["id"] == "16:00"
    assert len(times) == 8
