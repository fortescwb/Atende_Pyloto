"""Testes do prompt do OttoAgent."""

from __future__ import annotations

from ai.prompts.otto_prompt import OTTO_SYSTEM_PROMPT, format_otto_prompt


def test_system_prompt_requires_json() -> None:
    assert "JSON" in OTTO_SYSTEM_PROMPT


def test_system_prompt_mentions_pt_br() -> None:
    lowered = OTTO_SYSTEM_PROMPT.lower()
    assert "pt-br" in lowered or "portugues" in lowered


def test_system_prompt_mentions_fsm_guidelines() -> None:
    lowered = OTTO_SYSTEM_PROMPT.lower()
    assert "decisao de estado (fsm)" in lowered
    assert "handoff_human" in lowered


def test_system_prompt_includes_required_core_contexts() -> None:
    lowered = OTTO_SYSTEM_PROMPT.lower()
    assert "mindset comercial" in lowered
    assert "guardrails" in lowered
    assert "responda somente json" in lowered
    assert "message_type" in lowered


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


def test_format_otto_prompt_does_not_repeat_confidence_guidance() -> None:
    result = format_otto_prompt(
        user_message="Oi",
        session_state="TRIAGE",
        valid_transitions=["COLLECTING_INFO"],
        institutional_context="Empresa: Pyloto",
        tenant_context="Vertical: saas",
        contact_card_summary="Nome: Joao",
        conversation_history="Usuario: Oi",
    )

    assert "## Confidence (comercial)" not in result


def test_format_otto_prompt_mentions_operational_instruction() -> None:
    result = format_otto_prompt(
        user_message="Oi",
        session_state="TRIAGE",
        valid_transitions=["COLLECTING_INFO"],
        institutional_context="Empresa: Pyloto",
        tenant_context="Vertical: saas",
        contact_card_summary="Nome: Joao",
        conversation_history="Usuario: Oi",
    )

    assert "Instrucao operacional" in result
    assert "ContactCard + Historico" in result
