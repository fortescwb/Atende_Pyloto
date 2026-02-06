"""Smoke tests de prompts: cenários e budgets de tokens."""

from __future__ import annotations

import pytest

from ai.prompts.otto_prompt import build_full_prompt

tiktoken = pytest.importorskip("tiktoken")


def _count_tokens(text: str, *, model: str = "gpt-4o") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def test_prompt_no_intent_has_reasonable_token_budget() -> None:
    system_prompt, user_prompt, _ = build_full_prompt(
        contact_card_summary="(vazio)",
        conversation_history="Usuario: Oi",
        session_state="TRIAGE",
        valid_transitions=["COLLECTING_INFO", "GENERATING_RESPONSE"],
        user_message="Oi, tudo bem?",
        tenant_intent=None,
    )

    system_tokens = _count_tokens(system_prompt)
    user_tokens = _count_tokens(user_prompt)

    assert "contato@pyloto.com.br" in user_prompt
    assert system_tokens < 1200
    assert user_tokens < 2000
    assert system_tokens + user_tokens < 3000


def test_prompt_with_automacao_intent_injects_vertical_context() -> None:
    system_prompt, user_prompt, _ = build_full_prompt(
        contact_card_summary="Nome: Joao",
        conversation_history="Usuario: Quero um bot no WhatsApp",
        session_state="TRIAGE",
        valid_transitions=["COLLECTING_INFO", "GENERATING_RESPONSE"],
        user_message="Quero automatizar meu atendimento no WhatsApp",
        tenant_intent="automacao",
    )

    assert "automacao_atendimento" in user_prompt.lower()
    assert _count_tokens(system_prompt) < 1200
    assert _count_tokens(user_prompt) < 2000


def test_prompt_with_entregas_intent_injects_vertical_context() -> None:
    system_prompt, user_prompt, _ = build_full_prompt(
        contact_card_summary="(vazio)",
        conversation_history="Usuario: Preciso de motoboy",
        session_state="TRIAGE",
        valid_transitions=["COLLECTING_INFO", "GENERATING_RESPONSE"],
        user_message="Preciso de uma entrega hoje, tem motoboy?",
        tenant_intent="entregas",
    )

    assert "99161-9261" in user_prompt
    assert _count_tokens(system_prompt) < 1200
    assert _count_tokens(user_prompt) < 2000
