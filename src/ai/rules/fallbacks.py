"""Fallbacks determinísticos para quando LLM falha.

Garante resposta previsível e segura quando a IA não está disponível.
Conforme REGRAS_E_PADROES.md § 7: fallback seguro e determinístico.
Conforme FUNCIONAMENTO.md § 4.4: validação de saída e fallback seguro.
"""

from __future__ import annotations

from ai.config.settings import AIThresholdSettings, get_ai_settings
from ai.models.decision_agent import (
    FALLBACK_RESPONSE,
    DecisionAgentResult,
)
from ai.models.event_detection import EventDetectionResult
from ai.models.message_type_selection import MessageTypeSelectionResult
from ai.models.response_generation import ResponseGenerationResult
from ai.models.state_agent import StateAgentResult, SuggestedState


def get_fallback_confidence() -> float:
    """Retorna confiança padrão para fallbacks."""
    return get_ai_settings().thresholds.fallback_confidence


def fallback_event_detection(reason: str | None = None) -> EventDetectionResult:
    """Fallback determinístico para detecção de eventos.

    Usado quando:
    - LLM timeout
    - Erro de parsing de resposta
    - Resposta inválida

    Args:
        reason: Motivo do fallback (para rationale)

    Returns:
        EventDetectionResult com valores seguros e requires_followup=True
    """
    rationale = f"Fallback: {reason}" if reason else "Fallback: LLM indisponível"
    return EventDetectionResult(
        event="USER_SENT_TEXT",
        detected_intent="ENTRY_UNKNOWN",
        confidence=get_fallback_confidence(),
        requires_followup=True,
        rationale=rationale,
    )


def fallback_response_generation(reason: str | None = None) -> ResponseGenerationResult:
    """Fallback determinístico para geração de resposta.

    Usado quando:
    - LLM timeout
    - Erro de parsing de resposta
    - Resposta inválida

    Args:
        reason: Motivo do fallback (para rationale)

    Returns:
        ResponseGenerationResult com mensagem genérica e requires_human_review=True
    """
    rationale = f"Fallback: {reason}" if reason else "Fallback: LLM indisponível"
    return ResponseGenerationResult(
        text_content=(
            "Desculpe, não consegui processar sua mensagem no momento. "
            "Poderia reformular ou aguardar um instante?"
        ),
        options=(),
        suggested_next_state=None,
        requires_human_review=True,
        confidence=get_fallback_confidence(),
        rationale=rationale,
    )


def fallback_message_type_selection(
    reason: str | None = None,
) -> MessageTypeSelectionResult:
    """Fallback determinístico para seleção de tipo de mensagem.

    Usado quando:
    - LLM timeout
    - Erro de parsing de resposta
    - Resposta inválida

    Args:
        reason: Motivo do fallback (para rationale)

    Returns:
        MessageTypeSelectionResult com TEXT (mais seguro) e fallback=True
    """
    rationale = f"Fallback: {reason}" if reason else "Fallback: LLM indisponível"
    return MessageTypeSelectionResult(
        message_type="text",
        parameters={},
        confidence=get_fallback_confidence(),
        rationale=rationale,
        fallback=True,
    )


def should_require_human_review(
    confidence: float,
    thresholds: AIThresholdSettings | None = None,
) -> bool:
    """Determina se resposta deve ser revisada por humano.

    Args:
        confidence: Confiança da resposta de IA
        thresholds: Thresholds customizados (usa padrão se None)

    Returns:
        True se confiança está abaixo do threshold de revisão
    """
    if thresholds is None:
        thresholds = get_ai_settings().thresholds
    return confidence < thresholds.requires_review_threshold


def is_confidence_acceptable(
    confidence: float,
    thresholds: AIThresholdSettings | None = None,
) -> bool:
    """Verifica se confiança está acima do mínimo aceitável."""
    if thresholds is None:
        thresholds = get_ai_settings().thresholds
    return confidence >= thresholds.min_confidence


def fallback_state_suggestion(
    current_state: str,
    valid_transitions: tuple[str, ...] | None = None,
    reason: str | None = None,
) -> StateAgentResult:
    """Fallback determinístico para sugestão de estado."""
    rationale = f"Fallback: {reason}" if reason else "Fallback: LLM indisponível"
    fallback_state = "TRIAGE"
    if valid_transitions and fallback_state not in valid_transitions:
        fallback_state = valid_transitions[0] if valid_transitions else current_state

    return StateAgentResult(
        previous_state=current_state,
        current_state=current_state,
        suggested_next_states=(
            SuggestedState(state=fallback_state, confidence=0.5, reasoning=rationale),
        ),
        confidence=get_fallback_confidence(),
        rationale=rationale,
    )


def fallback_decision(
    consecutive_low_confidence: int = 0,
    reason: str | None = None,
) -> DecisionAgentResult:
    """Fallback determinístico para decisão final."""
    rationale = f"Fallback: {reason}" if reason else "Fallback: LLM indisponível"
    should_escalate = consecutive_low_confidence >= 3

    return DecisionAgentResult(
        final_state="TRIAGE",
        final_text=FALLBACK_RESPONSE,
        final_message_type="text",
        understood=False,
        confidence=get_fallback_confidence(),
        should_escalate=should_escalate,
        rationale=rationale,
    )
