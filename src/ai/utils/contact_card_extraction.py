"""Helpers de normalizacao para ContactCardExtractor."""

from __future__ import annotations

import unicodedata
from typing import Any

PRIMARY_INTEREST_ALIASES = {
    "gestao_perfis": "gestao_perfis_trafego",
    "trafego_pago": "gestao_perfis_trafego",
    "intermediacao": "intermediacao_entregas",
    "automacao": "automacao_atendimento",
    "automacao_whatsapp": "automacao_atendimento",
    "bot": "automacao_atendimento",
    "chatbot": "automacao_atendimento",
    "bot_whatsapp": "automacao_atendimento",
    "whatsapp_bot": "automacao_atendimento",
    "sistema_sob_medida": "sob_medida",
}

INT_FIELDS = {"message_volume_per_day", "attendants_count", "specialists_count", "users_count"}
BOOL_FIELDS_ALLOW_FALSE = {"has_crm", "needs_data_migration"}
TOOL_ALIASES = {
    "whatsapp": "whatsapp",
    "whatsapp_web": "whatsapp_web",
    "whatsappweb": "whatsapp_web",
    "planilha": "spreadsheet",
    "planilhas": "spreadsheet",
    "spreadsheet": "spreadsheet",
    "excel": "spreadsheet",
    "google_sheets": "spreadsheet",
    "crm": "crm",
    "erp": "erp",
    "agenda": "agenda",
    "api": "api",
}

STRING_LIST_FIELDS = {
    "modules_needed",
    "desired_features",
    "integrations_needed",
    "legacy_systems",
}


def parse_int_value(value: Any) -> int | None:
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        return int(value) if value >= 0 else None
    if isinstance(value, str):
        digits = "".join(ch for ch in value if ch.isdigit())
        if not digits:
            return None
        try:
            parsed = int(digits)
        except ValueError:
            return None
        return parsed if parsed >= 0 else None
    return None


def parse_bool_value(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = _strip_accents(value.strip().lower())
        if text in {"sim", "s", "yes", "y", "true", "1"}:
            return True
        if text in {"nao", "n", "no", "false", "0"}:
            return False
    return None


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )


def normalize_string_list(value: Any) -> list[str]:
    raw_items: list[str] = []
    if isinstance(value, list):
        raw_items = [str(item) for item in value if str(item).strip()]
    elif isinstance(value, str):
        text = value.replace(" e ", ",")
        raw_items = [part.strip() for part in text.split(",") if part.strip()]
    else:
        raw_items = [str(value).strip()] if value is not None else []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        cleaned = item.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def normalize_tools(value: Any) -> list[str]:
    raw_items: list[str] = []
    if isinstance(value, list):
        raw_items = [str(item) for item in value if str(item).strip()]
    elif isinstance(value, str):
        if " e " in value:
            value = value.replace(" e ", ",")
        raw_items = [part.strip() for part in value.split(",") if part.strip()]
    else:
        raw_items = [str(value).strip()] if value is not None else []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        if not item:
            continue
        key = item.strip().lower().replace(" ", "_").replace("-", "_")
        key = TOOL_ALIASES.get(key, key)
        if key and key not in seen:
            seen.add(key)
            normalized.append(key)
    return normalized


def normalize_meeting_mode(value: str) -> str:
    text = (value or "").strip().lower()
    if not text:
        return "online"
    if any(word in text for word in ("online", "remoto", "remote", "meet", "zoom", "teams")):
        return "online"
    if any(word in text for word in ("presencial", "pessoalmente", "local")):
        return "presencial"
    # Fallback seguro para evitar erro de validação.
    return "online"


def normalize_list_items(field: str, items: list[str]) -> list[str]:
    if not items:
        return []
    if field in {"modules_needed", "integrations_needed", "legacy_systems"}:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in items:
            key = item.strip().lower().replace(" ", "_").replace("-", "_")
            if not key or key in seen:
                continue
            seen.add(key)
            normalized.append(key)
        return normalized
    # desired_features: preserva texto, apenas trim/dedupe
    normalized_features: list[str] = []
    seen_features: set[str] = set()
    for item in items:
        text = item.strip()
        if not text:
            continue
        key = text.lower()
        if key in seen_features:
            continue
        seen_features.add(key)
        normalized_features.append(text)
    return normalized_features
