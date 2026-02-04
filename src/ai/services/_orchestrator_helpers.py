"""Helpers internos do orquestrador de IA.

Funções auxiliares extraídas de orchestrator.py para manter ≤200 linhas.
Conforme REGRAS_E_PADROES.md § 4: arquivos ≤200 linhas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai.models.decision_agent import CONFIDENCE_THRESHOLD, ESCALATION_CONSECUTIVE_FAILURES
from ai.rules.fallbacks import is_confidence_acceptable, should_require_human_review

if TYPE_CHECKING:
    from ai.models.event_detection import EventDetectionResult
    from ai.models.message_type_selection import MessageTypeSelectionResult
    from ai.models.response_generation import ResponseCandidate, ResponseGenerationResult
    from ai.models.state_agent import StateAgentResult


def calculate_overall_confidence(
    event_result: EventDetectionResult,
    response_result: ResponseGenerationResult,
    message_type_result: MessageTypeSelectionResult,
) -> float:
    """Calcula confiança geral (média ponderada).

    Pesos:
    - Event Detection: 40%
    - Response Generation: 40%
    - Message Type Selection: 20%
    """
    weights = (0.4, 0.4, 0.2)
    confidences = (
        event_result.confidence,
        response_result.confidence,
        message_type_result.confidence,
    )
    return sum(w * c for w, c in zip(weights, confidences, strict=True))


def calculate_4agent_confidence(
    state_result: StateAgentResult,
    response_result: ResponseGenerationResult,
    message_type_result: MessageTypeSelectionResult,
) -> float:
    """Calcula confiança para pipeline de 4 agentes.

    Pesos:
    - State Agent: 30%
    - Response Agent: 40%
    - Message Type Agent: 30%
    """
    weights = (0.3, 0.4, 0.3)
    confidences = (
        state_result.confidence,
        response_result.confidence,
        message_type_result.confidence,
    )
    return sum(w * c for w, c in zip(weights, confidences, strict=True))


def should_escalate(consecutive_low_confidence: int) -> bool:
    """Verifica se deve escalar para humano."""
    return consecutive_low_confidence >= ESCALATION_CONSECUTIVE_FAILURES


def select_best_candidate(
    candidates: tuple[ResponseCandidate, ...],
) -> ResponseCandidate | None:
    """Seleciona candidato com maior confiança."""
    if not candidates:
        return None
    return max(candidates, key=lambda c: c.confidence)


def is_understood(confidence: float) -> bool:
    """Verifica se resposta foi entendida (confiança acima do threshold)."""
    return confidence >= CONFIDENCE_THRESHOLD


def check_requires_review(
    event_result: EventDetectionResult,
    response_result: ResponseGenerationResult,
    sensitivity: str,
    needs_escalation: bool,
) -> bool:
    """Determina se resultado precisa de revisão humana."""
    if response_result.requires_human_review:
        return True
    if needs_escalation:
        return True
    if sensitivity in ("high", "critical"):
        return True
    if not is_confidence_acceptable(event_result.confidence):
        return True
    if not is_confidence_acceptable(response_result.confidence):
        return True
    if event_result.requires_followup:
        return should_require_human_review(event_result.confidence)
    return False
