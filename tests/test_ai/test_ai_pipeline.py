"""Testes de integração do pipeline de 4 agentes LLM.

Testa fluxo completo com MockAIClient.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from ai.models.decision_agent import (
    CONFIDENCE_THRESHOLD,
    FALLBACK_RESPONSE,
    DecisionAgentRequest,
    DecisionAgentResult,
)
from ai.models.event_detection import EventDetectionRequest, EventDetectionResult
from ai.models.message_type_selection import (
    MessageTypeSelectionRequest,
    MessageTypeSelectionResult,
)
from ai.models.response_generation import (
    ResponseGenerationRequest,
    ResponseGenerationResult,
    ResponseOption,
)
from ai.models.state_agent import StateAgentRequest, StateAgentResult, SuggestedState
from ai.services.orchestrator import AIOrchestrator, OrchestratorResult


@dataclass
class MockAIClient:
    """Mock do AIClientProtocol para testes."""

    state_confidence: float = 0.85
    response_confidence: float = 0.90
    decision_confidence: float = 0.88
    should_fail: bool = False

    async def detect_event(self, request: EventDetectionRequest) -> EventDetectionResult:
        """Mock de detect_event."""
        return EventDetectionResult(
            event="message",
            detected_intent="general",
            confidence=0.8,
            requires_followup=False,
            rationale="Mock",
        )

    async def suggest_state(self, request: StateAgentRequest) -> StateAgentResult:
        """Mock de suggest_state (Agente 1)."""
        if self.should_fail:
            return StateAgentResult(
                previous_state=request.current_state,
                current_state=request.current_state,
                suggested_next_states=(
                    SuggestedState(state="TRIAGE", confidence=0.3, reasoning="Fallback"),
                ),
                confidence=0.3,
                rationale="Fallback",
            )
        return StateAgentResult(
            previous_state=request.current_state,
            current_state=request.current_state,
            suggested_next_states=(
                SuggestedState(state="TRIAGE", confidence=self.state_confidence, reasoning="Mock"),
            ),
            confidence=self.state_confidence,
            rationale="Mock suggest_state",
        )

    async def generate_response(self, request: ResponseGenerationRequest) -> ResponseGenerationResult:
        """Mock de generate_response (Agente 2)."""
        if self.should_fail:
            return ResponseGenerationResult(
                text_content=FALLBACK_RESPONSE,
                options=[ResponseOption(id="fallback", title=FALLBACK_RESPONSE)],
                suggested_next_state=None,
                requires_human_review=False,
                confidence=0.3,
                rationale="Fallback",
            )
        return ResponseGenerationResult(
            text_content="Olá, como posso ajudar?",
            options=[ResponseOption(id="yes", title="Sim")],
            suggested_next_state="TRIAGE",
            requires_human_review=False,
            confidence=self.response_confidence,
            rationale="Mock response",
        )

    async def select_message_type(self, request: MessageTypeSelectionRequest) -> MessageTypeSelectionResult:
        """Mock de select_message_type (Agente 3)."""
        return MessageTypeSelectionResult(
            message_type="text",
            parameters={},
            confidence=0.95,
            rationale="Mock message type",
        )

    async def make_decision(self, request: DecisionAgentRequest) -> DecisionAgentResult:
        """Mock de make_decision (Agente 4)."""
        if self.should_fail:
            # Escala após 2+ falhas consecutivas (na 3ª chamada, contador=2)
            should_escalate = request.consecutive_low_confidence >= 2
            return DecisionAgentResult(
                final_state="INITIAL",
                final_text=FALLBACK_RESPONSE,
                final_message_type="text",
                understood=False,
                confidence=0.3,
                should_escalate=should_escalate,
                rationale="Fallback",
            )
        return DecisionAgentResult(
            final_state="TRIAGE",
            final_text="Olá, como posso ajudar?",
            final_message_type="text",
            understood=True,
            confidence=self.decision_confidence,
            should_escalate=False,
            rationale="Mock decision",
        )


class TestOrchestratorPipeline:
    """Testes do pipeline de 4 agentes."""

    @pytest.fixture
    def mock_client(self) -> MockAIClient:
        """Cria mock client."""
        return MockAIClient()

    @pytest.fixture
    def orchestrator(self, mock_client: MockAIClient) -> AIOrchestrator:
        """Cria orchestrator com mock client."""
        return AIOrchestrator(client=mock_client)

    @pytest.mark.asyncio
    async def test_happy_path_high_confidence(self, orchestrator: AIOrchestrator) -> None:
        """Fluxo feliz: confidence >= 0.7."""
        result = await orchestrator.process_message(
            user_input="Olá, preciso de ajuda",
            current_state="INITIAL",
        )
        assert isinstance(result, OrchestratorResult)
        assert result.understood is True
        assert result.overall_confidence >= CONFIDENCE_THRESHOLD
        assert result.should_escalate is False
        assert result.final_decision.final_text == "Olá, como posso ajudar?"

    @pytest.mark.asyncio
    async def test_result_contains_all_agent_outputs(self, orchestrator: AIOrchestrator) -> None:
        """Resultado contém outputs dos 4 agentes."""
        result = await orchestrator.process_message(user_input="Test", current_state="INITIAL")

        assert result.state_suggestion is not None
        assert result.response_generation is not None
        assert result.message_type_selection is not None
        assert result.final_decision is not None

    @pytest.mark.asyncio
    async def test_valid_transitions_passed_to_state_agent(self) -> None:
        """Transições válidas são passadas ao StateAgent."""
        mock_client = MockAIClient()
        orchestrator = AIOrchestrator(client=mock_client)

        await orchestrator.process_message(
            user_input="Olá",
            current_state="INITIAL",
            valid_transitions=("TRIAGE", "COLLECTING_INFO"),
        )
        # Se chegou aqui sem erro, passou as transições corretamente


class TestOrchestratorFallback:
    """Testes de fallback quando confidence baixa."""

    @pytest.fixture
    def failing_client(self) -> MockAIClient:
        """Cria mock client que simula falha."""
        return MockAIClient(should_fail=True)

    @pytest.fixture
    def failing_orchestrator(self, failing_client: MockAIClient) -> AIOrchestrator:
        """Cria orchestrator com client que falha."""
        return AIOrchestrator(client=failing_client)

    @pytest.mark.asyncio
    async def test_low_confidence_sets_understood_false(
        self, failing_orchestrator: AIOrchestrator
    ) -> None:
        """Baixa confiança marca understood=False."""
        result = await failing_orchestrator.process_message(
            user_input="asdfghjkl",
            current_state="INITIAL",
        )
        assert result.understood is False

    @pytest.mark.asyncio
    async def test_fallback_response_used(self, failing_orchestrator: AIOrchestrator) -> None:
        """Resposta fallback é usada quando confidence baixa."""
        result = await failing_orchestrator.process_message(
            user_input="???",
            current_state="INITIAL",
        )
        assert result.final_decision.final_text == FALLBACK_RESPONSE


class TestOrchestratorEscalation:
    """Testes de escalação após 3 falhas."""

    @pytest.mark.asyncio
    async def test_escalation_after_3_consecutive_failures(self) -> None:
        """Escala para humano após 3 falhas consecutivas."""
        mock_client = MockAIClient(should_fail=True)
        orchestrator = AIOrchestrator(client=mock_client)

        # Simula 3 falhas consecutivas
        for _ in range(3):
            result = await orchestrator.process_message(
                user_input="não entendo",
                current_state="INITIAL",
            )

        # Na 3ª falha, deve escalar
        assert result.should_escalate is True

    @pytest.mark.asyncio
    async def test_no_escalation_after_success(self) -> None:
        """Não escala se houver sucesso no meio."""
        mock_client = MockAIClient()
        orchestrator = AIOrchestrator(client=mock_client)

        # 2 falhas
        mock_client.should_fail = True
        await orchestrator.process_message(user_input="x", current_state="INITIAL")
        await orchestrator.process_message(user_input="y", current_state="INITIAL")

        # 1 sucesso (reseta contador)
        mock_client.should_fail = False
        await orchestrator.process_message(user_input="Olá", current_state="INITIAL")

        # Mais 2 falhas (não escala, precisa de 3 consecutivas)
        mock_client.should_fail = True
        result = await orchestrator.process_message(user_input="z", current_state="INITIAL")

        assert result.should_escalate is False
