"""Testes para ai/models/event_detection.py.

Valida contratos de detecção de eventos.
"""

import pytest

from ai.models.event_detection import EventDetectionRequest, EventDetectionResult


class TestEventDetectionRequest:
    """Testes para EventDetectionRequest."""

    def test_minimal_request(self) -> None:
        """Valida request com campos mínimos."""
        request = EventDetectionRequest(user_input="Olá")

        assert request.user_input == "Olá"
        assert request.session_history == []
        assert request.known_intent is None
        assert request.current_state is None

    def test_full_request(self) -> None:
        """Valida request com todos os campos."""
        request = EventDetectionRequest(
            user_input="Preciso de ajuda",
            session_history=["Olá", "Oi"],
            known_intent="SUPPORT",
            current_state="MENU",
        )

        assert request.user_input == "Preciso de ajuda"
        assert request.session_history == ["Olá", "Oi"]
        assert request.known_intent == "SUPPORT"
        assert request.current_state == "MENU"

    def test_immutable(self) -> None:
        """Valida que dataclass é imutável."""
        request = EventDetectionRequest(user_input="test")

        with pytest.raises(AttributeError):
            request.user_input = "outro"  # type: ignore[misc]


class TestEventDetectionResult:
    """Testes para EventDetectionResult."""

    def test_minimal_result(self) -> None:
        """Valida result com campos obrigatórios."""
        result = EventDetectionResult(
            event="USER_SENT_TEXT",
            detected_intent="GREETING",
            confidence=0.9,
        )

        assert result.event == "USER_SENT_TEXT"
        assert result.detected_intent == "GREETING"
        assert result.confidence == 0.9
        assert result.requires_followup is False
        assert result.rationale is None

    def test_full_result(self) -> None:
        """Valida result com todos os campos."""
        result = EventDetectionResult(
            event="USER_SENT_TEXT",
            detected_intent="SUPPORT_REQUEST",
            confidence=0.85,
            requires_followup=True,
            rationale="Usuário pediu ajuda",
        )

        assert result.event == "USER_SENT_TEXT"
        assert result.detected_intent == "SUPPORT_REQUEST"
        assert result.confidence == 0.85
        assert result.requires_followup is True
        assert result.rationale == "Usuário pediu ajuda"

    def test_confidence_clamped_above_one(self) -> None:
        """Valida que confiança > 1.0 é limitada a 1.0."""
        result = EventDetectionResult(
            event="USER_SENT_TEXT",
            detected_intent="TEST",
            confidence=1.5,
        )

        assert result.confidence == 1.0

    def test_confidence_clamped_below_zero(self) -> None:
        """Valida que confiança < 0.0 é limitada a 0.0."""
        result = EventDetectionResult(
            event="USER_SENT_TEXT",
            detected_intent="TEST",
            confidence=-0.5,
        )

        assert result.confidence == 0.0

    def test_immutable(self) -> None:
        """Valida que dataclass é imutável."""
        result = EventDetectionResult(
            event="USER_SENT_TEXT",
            detected_intent="TEST",
            confidence=0.8,
        )

        with pytest.raises(AttributeError):
            result.confidence = 0.5  # type: ignore[misc]
