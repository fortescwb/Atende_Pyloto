"""Testes para ai/models/message_type_selection.py.

Valida contratos de seleção de tipo de mensagem.
"""

import pytest

from ai.models.message_type_selection import (
    MessageTypeSelectionRequest,
    MessageTypeSelectionResult,
)


class TestMessageTypeSelectionRequest:
    """Testes para MessageTypeSelectionRequest."""

    def test_minimal_request(self) -> None:
        """Valida request com campos mínimos."""
        request = MessageTypeSelectionRequest(text_content="Olá!")

        assert request.text_content == "Olá!"
        assert request.options == []
        assert request.intent_type is None
        assert request.user_preference is None
        assert request.turn_count == 0

    def test_full_request(self) -> None:
        """Valida request com todos os campos."""
        request = MessageTypeSelectionRequest(
            text_content="Escolha uma opção:",
            options=[{"id": "1", "title": "Opção 1"}],
            intent_type="SUPPORT",
            user_preference="buttons",
            turn_count=3,
        )

        assert request.text_content == "Escolha uma opção:"
        assert len(request.options) == 1
        assert request.options[0]["title"] == "Opção 1"
        assert request.intent_type == "SUPPORT"
        assert request.user_preference == "buttons"
        assert request.turn_count == 3

    def test_immutable(self) -> None:
        """Valida que dataclass é imutável."""
        request = MessageTypeSelectionRequest(text_content="test")

        with pytest.raises(AttributeError):
            request.text_content = "outro"  # type: ignore[misc]


class TestMessageTypeSelectionResult:
    """Testes para MessageTypeSelectionResult."""

    def test_minimal_result(self) -> None:
        """Valida result com campo mínimo."""
        result = MessageTypeSelectionResult(message_type="text")

        assert result.message_type == "text"
        assert result.parameters == {}
        assert result.confidence == 0.8
        assert result.rationale is None
        assert result.fallback is False

    def test_full_result(self) -> None:
        """Valida result com todos os campos."""
        result = MessageTypeSelectionResult(
            message_type="interactive_button",
            parameters={"button_count": 3},
            confidence=0.95,
            rationale="Opções detectadas, usar botões",
            fallback=False,
        )

        assert result.message_type == "interactive_button"
        assert result.parameters == {"button_count": 3}
        assert result.confidence == 0.95
        assert result.rationale == "Opções detectadas, usar botões"
        assert result.fallback is False

    def test_fallback_result(self) -> None:
        """Valida result de fallback."""
        result = MessageTypeSelectionResult(
            message_type="text",
            fallback=True,
            rationale="Fallback: LLM timeout",
        )

        assert result.message_type == "text"
        assert result.fallback is True
        assert "Fallback" in result.rationale  # type: ignore[operator]

    def test_confidence_clamped(self) -> None:
        """Valida que confiança é limitada a 0.0-1.0."""
        result_high = MessageTypeSelectionResult(
            message_type="text",
            confidence=1.5,
        )
        assert result_high.confidence == 1.0

        result_low = MessageTypeSelectionResult(
            message_type="text",
            confidence=-0.5,
        )
        assert result_low.confidence == 0.0

    def test_immutable(self) -> None:
        """Valida que dataclass é imutável."""
        result = MessageTypeSelectionResult(message_type="text")

        with pytest.raises(AttributeError):
            result.message_type = "image"  # type: ignore[misc]
