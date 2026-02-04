"""Testes para ai/utils/agent_parser.py."""


from ai.utils.agent_parser import (
    parse_decision_agent_response,
    parse_response_candidates,
    parse_state_agent_response,
)


class TestParseStateAgentResponse:
    """Testes para parse_state_agent_response."""

    def test_valid_json(self) -> None:
        """Testa parsing de JSON válido."""
        raw = """{
            "previous_state": "INITIAL",
            "current_state": "TRIAGE",
            "suggested_next_states": [
                {"state": "COLLECTING_INFO", "confidence": 0.9, "reasoning": "teste"}
            ],
            "confidence": 0.85
        }"""
        result = parse_state_agent_response(raw)
        assert result.current_state == "TRIAGE"
        assert result.confidence == 0.85
        assert len(result.suggested_next_states) == 1

    def test_invalid_json_returns_fallback(self) -> None:
        """Testa que JSON inválido retorna fallback."""
        result = parse_state_agent_response("not json")
        assert result.confidence < 0.7
        assert "fallback" in (result.rationale or "").lower()

    def test_empty_string_returns_fallback(self) -> None:
        """Testa que string vazia retorna fallback."""
        result = parse_state_agent_response("")
        assert result.current_state == "INITIAL"  # default


class TestParseResponseCandidates:
    """Testes para parse_response_candidates."""

    def test_valid_json_with_candidates(self) -> None:
        """Testa parsing de JSON com candidatos."""
        raw = """{
            "candidates": [
                {"text_content": "Formal", "tone": "FORMAL", "confidence": 0.8},
                {"text_content": "Casual", "tone": "CASUAL", "confidence": 0.7}
            ]
        }"""
        candidates = parse_response_candidates(raw)
        assert len(candidates) == 2
        assert candidates[0].text_content == "Formal"

    def test_invalid_json_returns_fallback_candidate(self) -> None:
        """Testa que JSON inválido retorna fallback."""
        candidates = parse_response_candidates("not json")
        assert len(candidates) == 1
        assert "Desculpe" in candidates[0].text_content


class TestParseDecisionAgentResponse:
    """Testes para parse_decision_agent_response."""

    def test_valid_json(self) -> None:
        """Testa parsing de JSON válido."""
        raw = """{
            "final_state": "TRIAGE",
            "final_text": "Olá!",
            "final_message_type": "text",
            "confidence": 0.85
        }"""
        result = parse_decision_agent_response(raw)
        assert result.final_state == "TRIAGE"
        assert result.final_text == "Olá!"
        assert result.understood is True  # 0.85 >= 0.7

    def test_low_confidence_sets_understood_false(self) -> None:
        """Testa que baixa confiança marca understood=False."""
        raw = """{
            "final_state": "TRIAGE",
            "final_text": "Ok",
            "final_message_type": "text",
            "confidence": 0.5
        }"""
        result = parse_decision_agent_response(raw)
        assert result.understood is False

    def test_invalid_json_returns_fallback(self) -> None:
        """Testa que JSON inválido retorna fallback."""
        result = parse_decision_agent_response("not json")
        assert result.understood is False
        assert "Desculpe" in result.final_text

    def test_escalation_after_3_failures(self) -> None:
        """Testa escalação após 3 falhas consecutivas."""
        raw = '{"final_state": "X", "final_text": "Y", "final_message_type": "text", "confidence": 0.5}'
        result = parse_decision_agent_response(raw, consecutive_low_confidence=3)
        assert result.should_escalate is True
