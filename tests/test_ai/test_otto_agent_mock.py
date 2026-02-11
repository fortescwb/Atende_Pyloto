"""Testes do OttoAgent com mock LLM (P1-3).

Usa fixtures YAML para testes determinísticos sem chamadas reais ao LLM.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
import yaml

from ai.core.otto_client import OttoClientProtocol
from ai.models.otto import OttoDecision, OttoRequest
from ai.services.otto_agent import OttoAgentService


@pytest.fixture
def mock_fixtures() -> dict[str, Any]:
    """Carrega fixtures YAML de respostas mock do Otto."""
    fixtures_path = Path(__file__).parent.parent / "fixtures" / "otto_responses.yaml"
    with fixtures_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


@pytest.fixture
def mock_otto_client() -> AsyncMock:
    """Cliente mock do Otto que retorna respostas fixas."""
    client = AsyncMock(spec=OttoClientProtocol)
    return client


def _build_decision_from_fixture(fixture: dict[str, Any]) -> OttoDecision:
    """Constrói OttoDecision a partir de fixture."""
    response = fixture["response"]
    return OttoDecision(
        next_state=response["next_state"],
        response_text=response["response_text"],
        message_type=response["message_type"],
        confidence=response["confidence"],
        requires_human=response["requires_human"],
        reasoning_debug=response["reasoning_debug"],
    )


@pytest.mark.asyncio
async def test_triage_greeting(mock_fixtures: dict[str, Any], mock_otto_client: AsyncMock) -> None:
    """Testa saudação inicial movendo para TRIAGE."""
    fixture = mock_fixtures["triage_greeting"]
    expected_decision = _build_decision_from_fixture(fixture)
    mock_otto_client.decide.return_value = expected_decision

    service = OttoAgentService(mock_otto_client)
    request = OttoRequest(
        user_message=fixture["user_message"],
        session_state=fixture["current_state"],
        valid_transitions=["TRIAGE", "HANDOFF_HUMAN"],
        contact_card_summary="Nome: Usuario Teste",
        history=[],
        tenant_intent=None,
        intent_confidence=0.0,
        contact_card_signals={},
        loaded_contexts=[],
        correlation_id="test-001",
    )

    decision = await service.decide(request)

    assert decision.next_state == "TRIAGE"
    assert decision.confidence >= 0.9
    assert decision.requires_human is False
    assert "Otto" in decision.response_text


@pytest.mark.asyncio
async def test_collecting_info_automation(
    mock_fixtures: dict[str, Any], mock_otto_client: AsyncMock
) -> None:
    """Testa coleta de informações sobre automação."""
    fixture = mock_fixtures["collecting_info_automation"]
    expected_decision = _build_decision_from_fixture(fixture)
    mock_otto_client.decide.return_value = expected_decision

    service = OttoAgentService(mock_otto_client)
    request = OttoRequest(
        user_message=fixture["user_message"],
        session_state=fixture["current_state"],
        valid_transitions=["COLLECTING_INFO", "GENERATING_RESPONSE", "HANDOFF_HUMAN"],
        contact_card_summary="Nome: Usuario Teste",
        history=["Usuario: Oi", "Otto: Olá! Como posso ajudar?"],
        tenant_intent="automacao",
        intent_confidence=0.85,
        contact_card_signals={},
        loaded_contexts=[],
        correlation_id="test-002",
    )

    decision = await service.decide(request)

    assert decision.next_state == "COLLECTING_INFO"
    assert decision.confidence >= 0.8
    assert decision.requires_human is False
    assert "automação" in decision.response_text.lower()


@pytest.mark.asyncio
async def test_handoff_explicit_request(
    mock_fixtures: dict[str, Any], mock_otto_client: AsyncMock
) -> None:
    """Testa handoff quando usuário pede explicitamente."""
    fixture = mock_fixtures["handoff_explicit_request"]
    expected_decision = _build_decision_from_fixture(fixture)
    mock_otto_client.decide.return_value = expected_decision

    service = OttoAgentService(mock_otto_client)
    request = OttoRequest(
        user_message=fixture["user_message"],
        session_state=fixture["current_state"],
        valid_transitions=["COLLECTING_INFO", "HANDOFF_HUMAN"],
        contact_card_summary="Nome: Usuario Teste",
        history=[],
        tenant_intent=None,
        intent_confidence=0.0,
        contact_card_signals={},
        loaded_contexts=[],
        correlation_id="test-003",
    )

    decision = await service.decide(request)

    assert decision.next_state == "HANDOFF_HUMAN"
    assert decision.requires_human is True
    assert decision.confidence >= 0.95


@pytest.mark.asyncio
async def test_handoff_low_confidence(
    mock_fixtures: dict[str, Any], mock_otto_client: AsyncMock
) -> None:
    """Testa handoff quando confiança é baixa."""
    fixture = mock_fixtures["handoff_low_confidence"]
    expected_decision = _build_decision_from_fixture(fixture)
    mock_otto_client.decide.return_value = expected_decision

    service = OttoAgentService(mock_otto_client)
    request = OttoRequest(
        user_message=fixture["user_message"],
        session_state=fixture["current_state"],
        valid_transitions=["TRIAGE", "HANDOFF_HUMAN"],
        contact_card_summary="Nome: Usuario Teste",
        history=[],
        tenant_intent=None,
        intent_confidence=0.0,
        contact_card_signals={},
        loaded_contexts=[],
        correlation_id="test-004",
    )

    decision = await service.decide(request)

    assert decision.next_state == "HANDOFF_HUMAN"
    assert decision.requires_human is True
    assert decision.confidence < 0.5


@pytest.mark.asyncio
async def test_self_serve_info(mock_fixtures: dict[str, Any], mock_otto_client: AsyncMock) -> None:
    """Testa resposta self-service (FAQ)."""
    fixture = mock_fixtures["self_serve_prazo"]
    expected_decision = _build_decision_from_fixture(fixture)
    mock_otto_client.decide.return_value = expected_decision

    service = OttoAgentService(mock_otto_client)
    request = OttoRequest(
        user_message=fixture["user_message"],
        session_state=fixture["current_state"],
        valid_transitions=["SELF_SERVE_INFO", "GENERATING_RESPONSE", "HANDOFF_HUMAN"],
        contact_card_summary="Nome: Usuario Teste",
        history=["Usuario: Quero automação", "Otto: Ótimo! Me conta mais..."],
        tenant_intent="automacao",
        intent_confidence=0.9,
        contact_card_signals={},
        loaded_contexts=[],
        correlation_id="test-005",
    )

    decision = await service.decide(request)

    assert decision.next_state == "SELF_SERVE_INFO"
    assert decision.confidence >= 0.85
    assert decision.requires_human is False
    assert "prazo" in decision.response_text.lower()


@pytest.mark.asyncio
async def test_interactive_list_message_type(
    mock_fixtures: dict[str, Any], mock_otto_client: AsyncMock
) -> None:
    """Testa seleção de message_type interactive_list."""
    fixture = mock_fixtures["interactive_list_services"]
    expected_decision = _build_decision_from_fixture(fixture)
    mock_otto_client.decide.return_value = expected_decision

    service = OttoAgentService(mock_otto_client)
    request = OttoRequest(
        user_message=fixture["user_message"],
        session_state=fixture["current_state"],
        valid_transitions=["GENERATING_RESPONSE", "HANDOFF_HUMAN"],
        contact_card_summary="Nome: Usuario Teste",
        history=[],
        tenant_intent=None,
        intent_confidence=0.0,
        contact_card_signals={},
        loaded_contexts=[],
        correlation_id="test-006",
    )

    decision = await service.decide(request)

    assert decision.message_type == "interactive_list"
    assert decision.confidence >= 0.9
    assert decision.requires_human is False


@pytest.mark.asyncio
async def test_interactive_button_message_type(
    mock_fixtures: dict[str, Any], mock_otto_client: AsyncMock
) -> None:
    """Testa seleção de message_type interactive_button."""
    fixture = mock_fixtures["interactive_button_confirm"]
    expected_decision = _build_decision_from_fixture(fixture)
    mock_otto_client.decide.return_value = expected_decision

    service = OttoAgentService(mock_otto_client)
    request = OttoRequest(
        user_message=fixture["user_message"],
        session_state=fixture["current_state"],
        valid_transitions=["GENERATING_RESPONSE", "HANDOFF_HUMAN"],
        contact_card_summary="Nome: Usuario Teste",
        history=["Usuario: Quero saber mais", "Otto: Claro! O que te interessa?"],
        tenant_intent="automacao",
        intent_confidence=0.85,
        contact_card_signals={},
        loaded_contexts=[],
        correlation_id="test-007",
    )

    decision = await service.decide(request)

    assert decision.message_type == "interactive_button"
    assert decision.confidence >= 0.85
    assert decision.requires_human is False


@pytest.mark.asyncio
async def test_client_error_triggers_handoff(mock_otto_client: AsyncMock) -> None:
    """Testa que erro do client LLM resulta em handoff."""
    mock_otto_client.decide.side_effect = Exception("API Error")

    service = OttoAgentService(mock_otto_client)
    request = OttoRequest(
        user_message="Olá",
        session_state="INITIAL",
        valid_transitions=["TRIAGE", "HANDOFF_HUMAN"],
        contact_card_summary="Nome: Usuario Teste",
        history=[],
        tenant_intent=None,
        intent_confidence=0.0,
        contact_card_signals={},
        loaded_contexts=[],
        correlation_id="test-error",
    )

    decision = await service.decide(request)

    assert decision.next_state == "HANDOFF_HUMAN"
    assert decision.requires_human is True
    assert decision.confidence == 0.0
