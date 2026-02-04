"""Testes para ai/models/response_generation.py.

Valida contratos de geração de resposta.
"""

import pytest

from ai.models.response_generation import (
    ResponseGenerationRequest,
    ResponseGenerationResult,
    ResponseOption,
)


class TestResponseOption:
    """Testes para ResponseOption."""

    def test_minimal_option(self) -> None:
        """Valida option com campos mínimos."""
        option = ResponseOption(id="1", title="Opção 1")

        assert option.id == "1"
        assert option.title == "Opção 1"
        assert option.description is None

    def test_full_option(self) -> None:
        """Valida option com todos os campos."""
        option = ResponseOption(
            id="btn-1",
            title="Suporte",
            description="Solicitar suporte técnico",
        )

        assert option.id == "btn-1"
        assert option.title == "Suporte"
        assert option.description == "Solicitar suporte técnico"

    def test_immutable(self) -> None:
        """Valida que dataclass é imutável."""
        option = ResponseOption(id="1", title="Test")

        with pytest.raises(AttributeError):
            option.title = "outro"  # type: ignore[misc]


class TestResponseGenerationRequest:
    """Testes para ResponseGenerationRequest."""

    def test_full_request(self) -> None:
        """Valida request com todos os campos obrigatórios."""
        request = ResponseGenerationRequest(
            event="USER_SENT_TEXT",
            detected_intent="GREETING",
            current_state="ENTRY",
            next_state="MENU",
            user_input="Olá",
        )

        assert request.event == "USER_SENT_TEXT"
        assert request.detected_intent == "GREETING"
        assert request.current_state == "ENTRY"
        assert request.next_state == "MENU"
        assert request.user_input == "Olá"
        assert request.session_context == {}
        assert request.confidence_event == 0.5

    def test_with_session_context(self) -> None:
        """Valida request com contexto de sessão."""
        request = ResponseGenerationRequest(
            event="USER_SENT_TEXT",
            detected_intent="SUPPORT",
            current_state="ENTRY",
            next_state="SUPPORT_TICKET",
            user_input="Ajuda",
            session_context={"lead_name": "João"},
            confidence_event=0.9,
        )

        assert request.session_context == {"lead_name": "João"}
        assert request.confidence_event == 0.9


class TestResponseGenerationResult:
    """Testes para ResponseGenerationResult."""

    def test_minimal_result(self) -> None:
        """Valida result com campo mínimo."""
        result = ResponseGenerationResult(text_content="Olá!")

        assert result.text_content == "Olá!"
        assert result.options == ()
        assert result.suggested_next_state is None
        assert result.requires_human_review is False
        assert result.confidence == 0.8
        assert result.rationale is None

    def test_full_result(self) -> None:
        """Valida result com todos os campos."""
        option = ResponseOption(id="1", title="Suporte")
        result = ResponseGenerationResult(
            text_content="Como posso ajudar?",
            options=(option,),
            suggested_next_state="MENU",
            requires_human_review=True,
            confidence=0.95,
            rationale="Resposta gerada com sucesso",
        )

        assert result.text_content == "Como posso ajudar?"
        assert len(result.options) == 1
        assert result.options[0].title == "Suporte"
        assert result.suggested_next_state == "MENU"
        assert result.requires_human_review is True
        assert result.confidence == 0.95
        assert result.rationale == "Resposta gerada com sucesso"

    def test_text_truncation(self) -> None:
        """Valida que texto longo é truncado a 4096 chars."""
        long_text = "x" * 5000
        result = ResponseGenerationResult(text_content=long_text)

        assert len(result.text_content) == 4096
        assert result.text_content.endswith("...")

    def test_confidence_clamped(self) -> None:
        """Valida que confiança é limitada a 0.0-1.0."""
        result_high = ResponseGenerationResult(
            text_content="test",
            confidence=1.5,
        )
        assert result_high.confidence == 1.0

        result_low = ResponseGenerationResult(
            text_content="test",
            confidence=-0.5,
        )
        assert result_low.confidence == 0.0

    def test_immutable(self) -> None:
        """Valida que dataclass é imutável."""
        result = ResponseGenerationResult(text_content="test")

        with pytest.raises(AttributeError):
            result.text_content = "outro"  # type: ignore[misc]
