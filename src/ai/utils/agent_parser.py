"""Parser de respostas dos 4 agentes LLM.

Converte respostas JSON brutas para contratos tipados.
Conforme REGRAS_E_PADROES.md § 2.1: ai/utils contém utilitários.
"""

from __future__ import annotations

import logging
from typing import Any

from ai.models.decision_agent import (
    CONFIDENCE_THRESHOLD,
    FALLBACK_RESPONSE,
    DecisionAgentResult,
)
from ai.models.response_generation import ResponseCandidate, ResponseTone
from ai.models.state_agent import StateAgentResult, SuggestedState
from ai.rules.fallbacks import (
    fallback_decision,
    fallback_state_suggestion,
)
from ai.utils._json_extractor import extract_json_from_response

logger = logging.getLogger(__name__)


def parse_state_agent_response(
    raw_response: str,
    current_state: str = "INITIAL",
    valid_transitions: tuple[str, ...] | None = None,
) -> StateAgentResult:
    """Parseia resposta JSON do StateAgent (LLM #1)."""
    try:
        data = extract_json_from_response(raw_response)
        if data is None:
            return fallback_state_suggestion(current_state, valid_transitions, "no JSON")

        previous_state = str(data.get("previous_state", current_state))
        curr_state = str(data.get("current_state", current_state))
        confidence = float(data.get("confidence", 0.5))
        rationale = data.get("rationale")

        suggested_raw = data.get("suggested_next_states", [])
        suggested = _parse_suggested_states(suggested_raw)

        return StateAgentResult(
            previous_state=previous_state,
            current_state=curr_state,
            suggested_next_states=suggested,
            confidence=confidence,
            rationale=rationale if isinstance(rationale, str) else None,
        )
    except Exception as e:
        logger.warning("state_agent_parse_failed", extra={"error": str(e)})
        return fallback_state_suggestion(current_state, valid_transitions, str(e))


def _parse_suggested_states(raw: list[Any]) -> tuple[SuggestedState, ...]:
    """Parseia lista de estados sugeridos."""
    result = []
    for item in raw[:3]:  # Máximo 3 sugestões
        if isinstance(item, dict):
            result.append(
                SuggestedState(
                    state=str(item.get("state", "TRIAGE")),
                    confidence=float(item.get("confidence", 0.5)),
                    reasoning=str(item.get("reasoning", "")),
                )
            )
    return tuple(result) if result else (SuggestedState("TRIAGE", 0.5, "fallback"),)


def parse_response_candidates(raw_response: str) -> tuple[ResponseCandidate, ...]:
    """Parseia 3 candidatos de resposta do ResponseAgent (LLM #2)."""
    try:
        data = extract_json_from_response(raw_response)
        if data is None:
            return _fallback_candidates()

        candidates_raw = data.get("candidates", [])
        candidates = []
        for item in candidates_raw[:3]:
            if isinstance(item, dict):
                tone_str = str(item.get("tone", "formal")).upper()
                is_valid_tone = tone_str in ResponseTone.__members__
                tone = ResponseTone[tone_str] if is_valid_tone else ResponseTone.FORMAL
                candidates.append(
                    ResponseCandidate(
                        text_content=str(item.get("text_content", "")),
                        tone=tone,
                        confidence=float(item.get("confidence", 0.7)),
                        rationale=item.get("rationale"),
                    )
                )
        return tuple(candidates) if candidates else _fallback_candidates()
    except Exception as e:
        logger.warning("response_candidates_parse_failed", extra={"error": str(e)})
        return _fallback_candidates()


def _fallback_candidates() -> tuple[ResponseCandidate, ...]:
    """Retorna candidatos de fallback."""
    return (
        ResponseCandidate(FALLBACK_RESPONSE, ResponseTone.EMPATHETIC, 0.5, "fallback"),
    )


def parse_decision_agent_response(
    raw_response: str,
    consecutive_low_confidence: int = 0,
) -> DecisionAgentResult:
    """Parseia resposta JSON do DecisionAgent (LLM #4)."""
    try:
        data = extract_json_from_response(raw_response)
        if data is None:
            return fallback_decision(consecutive_low_confidence, "no JSON")

        confidence = float(data.get("confidence", 0.5))
        understood = confidence >= CONFIDENCE_THRESHOLD
        should_escalate = bool(data.get("should_escalate", False))

        if consecutive_low_confidence >= 3:
            should_escalate = True

        return DecisionAgentResult(
            final_state=str(data.get("final_state", "TRIAGE")),
            final_text=str(data.get("final_text", FALLBACK_RESPONSE)),
            final_message_type=str(data.get("final_message_type", "text")),
            understood=understood,
            confidence=confidence,
            should_escalate=should_escalate,
            rationale=data.get("rationale"),
        )
    except Exception as e:
        logger.warning("decision_agent_parse_failed", extra={"error": str(e)})
        return fallback_decision(consecutive_low_confidence, str(e))
