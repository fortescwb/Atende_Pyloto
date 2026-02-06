"""Testes deterministas para validacao de horario de reuniao."""

from __future__ import annotations

from app.services.meeting_time_validator import extract_hour, is_within_business_hours


def test_extract_hour_24h_h_suffix() -> None:
    assert extract_hour("Pode ser amanha as 14h") == 14


def test_extract_hour_24h_colon() -> None:
    assert extract_hour("Quinta 09:30, online") == 9


def test_extract_hour_am_pm() -> None:
    assert extract_hour("2pm, se puder") == 14


def test_extract_hour_da_tarde() -> None:
    assert extract_hour("Pode ser 6 da tarde") == 18


def test_extract_hour_meio_dia() -> None:
    assert extract_hour("meio dia serve") == 12


def test_is_within_business_hours_true() -> None:
    assert is_within_business_hours("amanha 10h") is True


def test_is_within_business_hours_false() -> None:
    assert is_within_business_hours("amanha 18h") is False


def test_is_within_business_hours_unknown() -> None:
    assert is_within_business_hours("amanha de manha") is None

