"""Testes dos helpers de normalização do ContactCardExtractor."""

from __future__ import annotations

from ai.utils.contact_card_extraction import (
    normalize_list_items,
    normalize_meeting_mode,
    normalize_string_list,
    normalize_tools,
    parse_bool_value,
    parse_int_value,
)


def test_parse_int_value_for_supported_types() -> None:
    assert parse_int_value(15) == 15
    assert parse_int_value(-2) is None
    assert parse_int_value(7.8) == 7
    assert parse_int_value("200 por dia") == 200
    assert parse_int_value("sem numero") is None
    assert parse_int_value(None) is None


def test_parse_int_value_handles_overflow_like_strings() -> None:
    huge_digits = "9" * 5000
    assert parse_int_value(huge_digits) is None


def test_parse_bool_value_with_accent_and_synonyms() -> None:
    assert parse_bool_value("sim") is True
    assert parse_bool_value("NÃO") is False
    assert parse_bool_value("yes") is True
    assert parse_bool_value("0") is False
    assert parse_bool_value("talvez") is None
    assert parse_bool_value(1) is None


def test_normalize_string_list_from_list_string_and_scalar() -> None:
    assert normalize_string_list(["CRM", "CRM", "  "]) == ["CRM"]
    assert normalize_string_list("crm, erp e api") == ["crm", "erp", "api"]
    assert normalize_string_list(123) == ["123"]
    assert normalize_string_list(None) == []


def test_normalize_tools_applies_aliases_and_dedupes() -> None:
    assert normalize_tools("WhatsApp Web, planilhas e CRM") == [
        "whatsapp_web",
        "spreadsheet",
        "crm",
    ]
    assert normalize_tools(["ERP", "erp", "agenda"]) == ["erp", "agenda"]
    assert normalize_tools(None) == []


def test_normalize_meeting_mode_online_presencial_and_fallback() -> None:
    assert normalize_meeting_mode("") == "online"
    assert normalize_meeting_mode("via zoom") == "online"
    assert normalize_meeting_mode("encontro presencial no local") == "presencial"
    assert normalize_meeting_mode("modo indefinido") == "online"


def test_normalize_list_items_for_modules_and_features() -> None:
    assert normalize_list_items("modules_needed", ["CRM", "crm", " API "]) == ["crm", "api"]
    assert normalize_list_items("integrations_needed", ["Hub Spot", "hub-spot"]) == ["hub_spot"]
    assert normalize_list_items("legacy_systems", ["Totvs", "TOTVS"]) == ["totvs"]
    assert normalize_list_items("desired_features", ["Relatorios", "relatorios", ""]) == [
        "Relatorios"
    ]
    assert normalize_list_items("desired_features", []) == []
