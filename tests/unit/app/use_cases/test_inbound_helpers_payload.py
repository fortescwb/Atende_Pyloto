"""Testes do builder de payload outbound (respeito ao message_type do Otto)."""

from __future__ import annotations

from types import SimpleNamespace

from app.use_cases.whatsapp._inbound_helpers import build_outbound_payload


def test_build_outbound_payload_uses_interactive_button_from_decision() -> None:
    decision = SimpleNamespace(
        response_text="Escolha uma opcao",
        message_type="interactive_button",
        final_text=None,
        final_message_type=None,
    )

    payload = build_outbound_payload(decision, "+554499999999")

    assert payload["type"] == "interactive"
    assert payload["interactive"]["type"] == "button"


def test_build_outbound_payload_uses_interactive_list_from_decision() -> None:
    decision = SimpleNamespace(
        response_text="Veja as opcoes",
        message_type="interactive_list",
        final_text=None,
        final_message_type=None,
    )

    payload = build_outbound_payload(decision, "+554499999999")

    assert payload["type"] == "interactive"
    assert payload["interactive"]["type"] == "list"
