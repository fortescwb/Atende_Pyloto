"""Testes do OttoAgentService."""

from __future__ import annotations

import pytest

from ai.models.otto import OttoDecision, OttoRequest
from ai.services.otto_agent import OttoAgentService


class FakeClient:
    """Fake client para simular respostas do Otto."""

    def __init__(self, decision: OttoDecision | None) -> None:
        self._decision = decision

    async def decide(self, *, system_prompt: str, user_prompt: str) -> OttoDecision | None:
        return self._decision


def _base_request() -> OttoRequest:
    return OttoRequest(
        user_message="Oi",
        session_state="TRIAGE",
        history=["Usuario: Oi", "Otto: Olá"],
        contact_card_summary="Nome: Joao",
        tenant_context="Vertical: saas",
        valid_transitions=["COLLECTING_INFO", "GENERATING_RESPONSE"],
    )


@pytest.mark.asyncio
async def test_valid_decision_passes() -> None:
    decision = OttoDecision(
        next_state="COLLECTING_INFO",
        response_text="Posso te fazer algumas perguntas rapidas?",
        message_type="text",
        confidence=0.9,
        requires_human=False,
    )
    service = OttoAgentService(FakeClient(decision))

    result = await service.decide(_base_request())

    assert result.next_state == "COLLECTING_INFO"
    assert result.requires_human is False


@pytest.mark.asyncio
async def test_invalid_transition_triggers_handoff() -> None:
    decision = OttoDecision(
        next_state="ERROR",
        response_text="Resposta qualquer",
        message_type="text",
        confidence=0.9,
        requires_human=False,
    )
    service = OttoAgentService(FakeClient(decision))

    result = await service.decide(_base_request())

    assert result.next_state == "HANDOFF_HUMAN"
    assert result.requires_human is True


@pytest.mark.asyncio
async def test_pii_triggers_handoff() -> None:
    decision = OttoDecision(
        next_state="GENERATING_RESPONSE",
        response_text="Seu email e user@example.com",
        message_type="text",
        confidence=0.9,
        requires_human=False,
    )
    service = OttoAgentService(FakeClient(decision))

    result = await service.decide(_base_request())

    assert result.next_state == "HANDOFF_HUMAN"
    assert result.requires_human is True


@pytest.mark.asyncio
async def test_low_confidence_triggers_handoff() -> None:
    decision = OttoDecision(
        next_state="GENERATING_RESPONSE",
        response_text="Entendi.",
        message_type="text",
        confidence=0.5,
        requires_human=False,
    )
    service = OttoAgentService(FakeClient(decision))

    result = await service.decide(_base_request())

    assert result.next_state == "HANDOFF_HUMAN"
    assert result.requires_human is True


@pytest.mark.asyncio
async def test_gray_zone_sets_requires_human_flag() -> None:
    decision = OttoDecision(
        next_state="GENERATING_RESPONSE",
        response_text="Entendi sua necessidade.",
        message_type="text",
        confidence=0.75,
        requires_human=False,
    )
    service = OttoAgentService(FakeClient(decision))

    result = await service.decide(_base_request())

    assert result.next_state == "GENERATING_RESPONSE"
    assert result.requires_human is True
