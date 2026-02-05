"""Testes do prompt do OttoAgent."""

from __future__ import annotations

from ai.prompts.otto_prompt import OTTO_SYSTEM_PROMPT, format_otto_prompt


def test_system_prompt_requires_json() -> None:
    assert "JSON" in OTTO_SYSTEM_PROMPT


def test_system_prompt_mentions_pt_br() -> None:
    assert "PT-BR" in OTTO_SYSTEM_PROMPT or "portugues" in OTTO_SYSTEM_PROMPT.lower()


def test_format_otto_prompt_injects_context() -> None:
    result = format_otto_prompt(
        user_message="Oi",
        session_state="TRIAGE",
        valid_transitions=["COLLECTING_INFO", "GENERATING_RESPONSE"],
        institutional_context="Empresa: Pyloto",
        tenant_context="Vertical: saas",
        contact_card_summary="Nome: Joao",
        conversation_history="Usuario: Oi",
    )

    assert "Empresa: Pyloto" in result
    assert "Nome: Joao" in result
    assert "TRIAGE" in result
    assert "COLLECTING_INFO" in result
