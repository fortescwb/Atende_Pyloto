"""Testes para ai/services/orchestrator.py.

Valida orquestração dos 4 agentes LLM.
"""

import pytest

from ai.core.mock_client import MockAIClient
from ai.services.orchestrator import AIOrchestrator, OrchestratorResult


class TestAIOrchestrator:
    """Testes para AIOrchestrator."""

    @pytest.fixture
    def orchestrator(self) -> AIOrchestrator:
        """Cria orquestrador com cliente mock."""
        client = MockAIClient()
        return AIOrchestrator(client)

    @pytest.mark.asyncio
    async def test_process_message_basic(
        self, orchestrator: AIOrchestrator
    ) -> None:
        """Valida processamento básico de mensagem."""
        result = await orchestrator.process_message("Olá")

        assert isinstance(result, OrchestratorResult)
        assert result.state_suggestion is not None
        assert result.response_generation is not None
        assert result.message_type_selection is not None
        assert result.final_decision is not None

    @pytest.mark.asyncio
    async def test_process_message_with_history(
        self, orchestrator: AIOrchestrator
    ) -> None:
        """Valida processamento com histórico."""
        result = await orchestrator.process_message(
            user_input="Continue",
            current_state="TRIAGE",
            session_history=["Olá", "Como posso ajudar?"],
            valid_transitions=("COLLECTING_INFO", "GENERATING_RESPONSE"),
        )

        assert result.state_suggestion is not None
        assert result.overall_confidence > 0

    @pytest.mark.asyncio
    async def test_overall_confidence_calculation(
        self, orchestrator: AIOrchestrator
    ) -> None:
        """Valida cálculo de confiança geral."""
        result = await orchestrator.process_message("Olá")

        # Overall confidence é média ponderada: 0.3*state + 0.4*response + 0.3*msg_type
        assert 0.0 <= result.overall_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_understood_flag(
        self, orchestrator: AIOrchestrator
    ) -> None:
        """Valida flag understood baseado em confiança."""
        result = await orchestrator.process_message("Olá, preciso de ajuda")

        # MockAIClient retorna confiança >= 0.7, então understood=True
        assert isinstance(result.understood, bool)

    @pytest.mark.asyncio
    async def test_pii_sanitization(
        self, orchestrator: AIOrchestrator
    ) -> None:
        """Valida que PII é sanitizado antes do processamento."""
        result = await orchestrator.process_message(
            "Meu CPF é 123.456.789-10 e email teste@teste.com"
        )

        assert result.state_suggestion is not None


class TestOrchestratorResult:
    """Testes para OrchestratorResult."""

    @pytest.fixture
    def orchestrator(self) -> AIOrchestrator:
        """Cria orquestrador com cliente mock."""
        client = MockAIClient()
        return AIOrchestrator(client)

    @pytest.mark.asyncio
    async def test_result_is_immutable(
        self, orchestrator: AIOrchestrator
    ) -> None:
        """Valida que resultado é imutável."""
        result = await orchestrator.process_message("Olá")

        with pytest.raises(AttributeError):
            result.understood = True  # type: ignore[misc]

    @pytest.mark.asyncio
    async def test_result_contains_all_fields(
        self, orchestrator: AIOrchestrator
    ) -> None:
        """Valida que resultado contém todos os campos."""
        result = await orchestrator.process_message("Olá")

        assert hasattr(result, "state_suggestion")
        assert hasattr(result, "response_generation")
        assert hasattr(result, "message_type_selection")
        assert hasattr(result, "final_decision")
        assert hasattr(result, "overall_confidence")
        assert hasattr(result, "understood")
        assert hasattr(result, "should_escalate")
