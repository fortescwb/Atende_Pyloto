"""Testes para ai/rules/fallbacks.py.

Valida funções de fallback determinístico.
"""

from ai.rules.fallbacks import (
    fallback_event_detection,
    fallback_message_type_selection,
    fallback_response_generation,
    get_fallback_confidence,
    is_confidence_acceptable,
    should_require_human_review,
)


class TestGetFallbackConfidence:
    """Testes para get_fallback_confidence."""

    def test_returns_float(self) -> None:
        """Valida que retorna float."""
        result = get_fallback_confidence()
        assert isinstance(result, float)

    def test_returns_low_confidence(self) -> None:
        """Valida que retorna confiança baixa."""
        result = get_fallback_confidence()
        assert 0.0 <= result <= 0.5


class TestFallbackEventDetection:
    """Testes para fallback_event_detection."""

    def test_returns_result(self) -> None:
        """Valida que retorna EventDetectionResult."""
        result = fallback_event_detection()

        assert result.event == "USER_SENT_TEXT"
        assert result.detected_intent == "ENTRY_UNKNOWN"
        assert result.requires_followup is True

    def test_with_reason(self) -> None:
        """Valida que reason aparece no rationale."""
        result = fallback_event_detection(reason="timeout")

        assert "timeout" in (result.rationale or "")

    def test_without_reason(self) -> None:
        """Valida fallback sem reason."""
        result = fallback_event_detection()

        assert result.rationale is not None
        assert "Fallback" in result.rationale

    def test_confidence_is_low(self) -> None:
        """Valida que confiança é baixa."""
        result = fallback_event_detection()

        assert result.confidence <= 0.5


class TestFallbackResponseGeneration:
    """Testes para fallback_response_generation."""

    def test_returns_result(self) -> None:
        """Valida que retorna ResponseGenerationResult."""
        result = fallback_response_generation()

        assert result.text_content != ""
        assert result.requires_human_review is True

    def test_with_reason(self) -> None:
        """Valida que reason aparece no rationale."""
        result = fallback_response_generation(reason="parsing error")

        assert "parsing error" in (result.rationale or "")

    def test_generic_message(self) -> None:
        """Valida mensagem genérica de fallback."""
        result = fallback_response_generation()

        assert "Desculpe" in result.text_content or "não consegui" in result.text_content

    def test_confidence_is_low(self) -> None:
        """Valida que confiança é baixa."""
        result = fallback_response_generation()

        assert result.confidence <= 0.5


class TestFallbackMessageTypeSelection:
    """Testes para fallback_message_type_selection."""

    def test_returns_text_type(self) -> None:
        """Valida que retorna tipo text (mais seguro)."""
        result = fallback_message_type_selection()

        assert result.message_type == "text"

    def test_fallback_flag_is_true(self) -> None:
        """Valida que flag fallback é True."""
        result = fallback_message_type_selection()

        assert result.fallback is True

    def test_with_reason(self) -> None:
        """Valida que reason aparece no rationale."""
        result = fallback_message_type_selection(reason="LLM error")

        assert "LLM error" in (result.rationale or "")


class TestShouldRequireHumanReview:
    """Testes para should_require_human_review."""

    def test_low_confidence_requires_review(self) -> None:
        """Valida que confiança baixa requer revisão."""
        result = should_require_human_review(0.3)
        assert result is True

    def test_high_confidence_no_review(self) -> None:
        """Valida que confiança alta não requer revisão."""
        result = should_require_human_review(0.9)
        assert result is False


class TestIsConfidenceAcceptable:
    """Testes para is_confidence_acceptable."""

    def test_high_confidence_acceptable(self) -> None:
        """Valida que confiança alta é aceitável."""
        result = is_confidence_acceptable(0.9)
        assert result is True

    def test_low_confidence_not_acceptable(self) -> None:
        """Valida que confiança baixa não é aceitável."""
        result = is_confidence_acceptable(0.2)
        assert result is False

    def test_edge_case(self) -> None:
        """Valida caso limite (threshold agora é 0.7)."""
        # Com threshold 0.7, confiança de 0.7 deve ser aceita
        result = is_confidence_acceptable(0.7)
        assert result is True

        # Confiança de 0.5 não é mais aceita (abaixo do threshold 0.7)
        result_low = is_confidence_acceptable(0.5)
        assert result_low is False
