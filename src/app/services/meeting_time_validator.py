"""Validacao deterministica de horario de reuniao (sem LLM).

Regra de negocio:
- Aceitar apenas horarios dentro do expediente da Pyloto (09h-17h).

Este modulo nao tenta resolver datas/timezones. O objetivo e:
- extrair um horario (hora) quando o usuario informa explicitamente
- permitir/recusar de forma previsivel
"""

from __future__ import annotations

import re
import unicodedata


def is_within_business_hours(
    text: str,
    *,
    start_hour: int = 9,
    end_hour: int = 17,
) -> bool | None:
    """Retorna True/False quando conseguir extrair a hora; None quando nao for possivel."""
    hour = extract_hour(text)
    if hour is None:
        return None
    return start_hour <= hour <= end_hour


def extract_hour(text: str) -> int | None:
    """Extrai hora (0-23) a partir de texto livre. Retorna None se indefinido."""
    normalized = _normalize(text)
    if not normalized:
        return None

    special = _extract_special_hour(normalized)
    if special is not None:
        return special
    for extractor in (
        _extract_colon_hour,
        _extract_hora_hour,
        _extract_am_pm_hour,
        _extract_evening_hour,
        _extract_morning_hour,
    ):
        hour = extractor(normalized)
        if hour is not None:
            return hour
    return None


def _normalize(text: str) -> str:
    lowered = (text or "").strip().lower()
    if not lowered:
        return ""
    no_accents = "".join(
        ch for ch in unicodedata.normalize("NFKD", lowered) if not unicodedata.combining(ch)
    )
    return " ".join(no_accents.split())


def _to_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def _extract_special_hour(normalized: str) -> int | None:
    if "meio dia" in normalized or "meio-dia" in normalized:
        return 12
    if "meia noite" in normalized or "meia-noite" in normalized:
        return 0
    return None


def _extract_colon_hour(normalized: str) -> int | None:
    match = re.search(r"(?<!\d)(\d{1,2})\s*:\s*(\d{2})(?!\d)", normalized)
    return _safe_hour(_to_int(match.group(1))) if match else None


def _extract_hora_hour(normalized: str) -> int | None:
    match = re.search(r"(?<!\d)(\d{1,2})\s*(h|hs|hora|horas)(?!\w)", normalized)
    return _safe_hour(_to_int(match.group(1))) if match else None


def _extract_am_pm_hour(normalized: str) -> int | None:
    match = re.search(r"(?<!\d)(\d{1,2})\s*(am|pm)(?!\w)", normalized)
    if not match:
        return None
    hour = _to_int(match.group(1))
    if hour is None:
        return None
    suffix = match.group(2)
    if suffix == "pm" and 1 <= hour <= 11:
        hour += 12
    if suffix == "am" and hour == 12:
        hour = 0
    return _safe_hour(hour)


def _extract_evening_hour(normalized: str) -> int | None:
    match = re.search(r"(?<!\d)(\d{1,2})\s*(da|de)\s*(tarde|noite)(?!\w)", normalized)
    if not match:
        return None
    hour = _to_int(match.group(1))
    if hour is None:
        return None
    if 1 <= hour <= 11:
        hour += 12
    return _safe_hour(hour)


def _extract_morning_hour(normalized: str) -> int | None:
    match = re.search(r"(?<!\d)(\d{1,2})\s*(da|de)\s*(manha)(?!\w)", normalized)
    return _safe_hour(_to_int(match.group(1))) if match else None


def _safe_hour(hour: int | None) -> int | None:
    if hour is None:
        return None
    return hour if 0 <= hour <= 23 else None
