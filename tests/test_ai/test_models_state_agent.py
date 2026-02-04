"""Testes para ai/models/state_agent.py."""

import pytest

from ai.models.state_agent import StateAgentRequest, StateAgentResult, SuggestedState


class TestSuggestedState:
    """Testes para SuggestedState."""

    def test_create_valid(self) -> None:
        """Testa criação com valores válidos."""
        state = SuggestedState(state="TRIAGE", confidence=0.8, reasoning="test")
        assert state.state == "TRIAGE"
        assert state.confidence == 0.8
        assert state.reasoning == "test"

    def test_confidence_clamp_high(self) -> None:
        """Testa que confiança > 1.0 é clamped para 1.0."""
        state = SuggestedState(state="TRIAGE", confidence=1.5, reasoning="")
        assert state.confidence == 1.0

    def test_confidence_clamp_low(self) -> None:
        """Testa que confiança < 0.0 é clamped para 0.0."""
        state = SuggestedState(state="TRIAGE", confidence=-0.5, reasoning="")
        assert state.confidence == 0.0

    def test_empty_state_raises(self) -> None:
        """Testa que estado vazio levanta ValueError."""
        with pytest.raises(ValueError, match="state não pode ser vazio"):
            SuggestedState(state="", confidence=0.5, reasoning="test")


class TestStateAgentRequest:
    """Testes para StateAgentRequest."""

    def test_create_valid(self) -> None:
        """Testa criação com valores válidos."""
        request = StateAgentRequest(
            user_input="Olá",
            current_state="INITIAL",
            conversation_history="histórico",
            valid_transitions=("TRIAGE", "COLLECTING_INFO"),
        )
        assert request.user_input == "Olá"
        assert request.current_state == "INITIAL"
        assert "TRIAGE" in request.valid_transitions

    def test_empty_user_input_raises(self) -> None:
        """Testa que user_input vazio levanta ValueError."""
        with pytest.raises(ValueError):
            StateAgentRequest(
                user_input="",
                current_state="INITIAL",
                conversation_history="",
                valid_transitions=(),
            )


class TestStateAgentResult:
    """Testes para StateAgentResult."""

    def test_create_valid(self) -> None:
        """Testa criação com valores válidos."""
        result = StateAgentResult(
            previous_state="INITIAL",
            current_state="TRIAGE",
            suggested_next_states=(
                SuggestedState("COLLECTING_INFO", 0.9, "motivo"),
            ),
            confidence=0.85,
            rationale="análise",
        )
        assert result.previous_state == "INITIAL"
        assert result.current_state == "TRIAGE"
        assert len(result.suggested_next_states) == 1

    def test_max_three_suggestions(self) -> None:
        """Testa que máximo de 3 sugestões é respeitado."""
        suggestions = tuple(
            SuggestedState(f"STATE_{i}", 0.5, "") for i in range(5)
        )
        result = StateAgentResult(
            previous_state="A",
            current_state="B",
            suggested_next_states=suggestions,
            confidence=0.7,
        )
        assert len(result.suggested_next_states) == 3

    def test_confidence_clamp(self) -> None:
        """Testa que confiança é normalizada."""
        result = StateAgentResult(
            previous_state="A",
            current_state="B",
            suggested_next_states=(),
            confidence=1.5,
        )
        assert result.confidence == 1.0
