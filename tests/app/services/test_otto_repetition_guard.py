"""Testes para o guard de repeticao de perguntas do Otto."""

from __future__ import annotations

from ai.models.otto import OttoDecision
from app.domain.contact_card import ContactCard
from app.services.otto_repetition_guard import apply_continuation_guard, apply_repetition_guard


def _contact_card(**kwargs) -> ContactCard:
    base = {
        "wa_id": "551199999999",
        "phone": "551199999999",
        "whatsapp_name": "Teste",
    }
    base.update(kwargs)
    return ContactCard(**base)


def test_guard_applies_when_volume_known() -> None:
    contact_card = _contact_card(message_volume_per_day=200)
    decision = OttoDecision(
        next_state="COLLECTING_INFO",
        response_text="Quantas mensagens por dia voce recebe?",
        message_type="text",
    )
    result = apply_repetition_guard(decision=decision, contact_card=contact_card)
    assert result.applied is True
    assert "200" in result.decision.response_text


def test_guard_skips_when_volume_missing() -> None:
    contact_card = _contact_card()
    decision = OttoDecision(
        next_state="COLLECTING_INFO",
        response_text="Quantas mensagens por dia voce recebe?",
        message_type="text",
    )
    result = apply_repetition_guard(decision=decision, contact_card=contact_card)
    assert result.applied is False


def test_continuation_guard_appends_next_step_on_confirmation() -> None:
    contact_card = _contact_card(
        message_volume_per_day=200,
        attendants_count=2,
        specialists_count=2,
    )
    decision = OttoDecision(
        next_state="COLLECTING_INFO",
        response_text="Entendi, voce recebe cerca de 200 mensagens por dia.",
        message_type="text",
    )
    result = apply_continuation_guard(
        decision=decision,
        contact_card=contact_card,
        user_message="isso",
    )
    assert result.applied is True
    assert "necessidade" in result.decision.response_text.lower()
