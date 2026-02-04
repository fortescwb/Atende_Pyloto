"""Testes para ai/models/decision_agent.py."""

import pytest

from ai.models.decision_agent import (
    CONFIDENCE_THRESHOLD,
    ESCALATION_CONSECUTIVE_FAILURES,
    FALLBACK_RESPONSE,
    DecisionAgentResult,
)


class TestDecisionAgentConstants:
    """Testes para constantes."""

    def test_threshold_is_0_7(self) -> None:
        """Valida threshold de confiança."""
        assert CONFIDENCE_THRESHOLD == 0.7

    def test_escalation_is_3(self) -> None:
        """Valida falhas consecutivas para escalação."""
        assert ESCALATION_CONSECUTIVE_FAILURES == 3

    def test_fallback_response_exists(self) -> None:
        """Valida que fallback response existe."""
        assert len(FALLBACK_RESPONSE) > 0


class TestDecisionAgentResult:
    """Testes para DecisionAgentResult."""

    def test_create_valid(self) -> None:
        """Testa criação com valores válidos."""
        result = DecisionAgentResult(
            final_state="TRIAGE",
            final_text="Olá!",
            final_message_type="text",
            understood=True,
            confidence=0.85,
        )
        assert result.final_state == "TRIAGE"
        assert result.final_text == "Olá!"
        assert result.understood is True

    def test_understood_derived_from_confidence_high(self) -> None:
        """Testa que understood=True quando confidence >= 0.7."""
        result = DecisionAgentResult(
            final_state="TRIAGE",
            final_text="Ok",
            final_message_type="text",
            understood=False,  # será corrigido
            confidence=0.8,
        )
        assert result.understood is True

    def test_understood_derived_from_confidence_low(self) -> None:
        """Testa que understood=False quando confidence < 0.7."""
        result = DecisionAgentResult(
            final_state="TRIAGE",
            final_text="Ok",
            final_message_type="text",
            understood=True,  # será corrigido
            confidence=0.5,
        )
        assert result.understood is False

    def test_confidence_clamp(self) -> None:
        """Testa que confiança é normalizada."""
        result = DecisionAgentResult(
            final_state="A",
            final_text="B",
            final_message_type="text",
            understood=True,
            confidence=1.5,
        )
        assert result.confidence == 1.0

    def test_should_escalate_default_false(self) -> None:
        """Testa que should_escalate default é False."""
        result = DecisionAgentResult(
            final_state="A",
            final_text="B",
            final_message_type="text",
            understood=True,
            confidence=0.9,
        )
        assert result.should_escalate is False

    def test_immutable(self) -> None:
        """Testa que resultado é imutável."""
        result = DecisionAgentResult(
            final_state="A",
            final_text="B",
            final_message_type="text",
            understood=True,
            confidence=0.9,
        )
        with pytest.raises(AttributeError):
            result.final_text = "modified"  # type: ignore[misc]
