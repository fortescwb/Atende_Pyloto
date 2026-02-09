"""Testes do OttoAgentService."""

from __future__ import annotations

import pytest

from ai.models.otto import OttoDecision, OttoRequest
from ai.services.otto_agent import OttoAgentService, _conversation_history_text


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
        tenant_intent="saas",
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

    assert result == decision


@pytest.mark.asyncio
async def test_client_error_returns_handoff() -> None:
    service = OttoAgentService(FakeClient(None))

    result = await service.decide(_base_request())

    assert result.next_state == "HANDOFF_HUMAN"
    assert result.requires_human is True


def test_conversation_history_uses_last_20_messages() -> None:
    history = [f"Usuario: msg {idx}" for idx in range(1, 31)]

    text = _conversation_history_text(history)
    lines = text.splitlines()

    assert len(lines) == 20
    assert lines[0] == "Usuario: msg 11"
    assert lines[-1] == "Usuario: msg 30"


def test_conversation_history_normalizes_assistant_label_to_otto() -> None:
    text = _conversation_history_text(["assistente: tudo certo"])
    assert text == "Otto: tudo certo"
