"""Helpers internos para MasterDecider.

Módulo interno (prefixo _) contendo funções auxiliares.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai.services.orchestrator import OrchestratorResult

# Palavras que forçam encerramento imediato
FORCE_CLOSE_KEYWORDS: frozenset[str] = frozenset({
    "encerrar",
    "cancelar",
    "sair",
    "parar",
    "desistir",
})

# Palavras que forçam escalação humana
FORCE_ESCALATION_KEYWORDS: frozenset[str] = frozenset({
    "humano",
    "atendente",
    "pessoa",
    "gerente",
    "supervisor",
    "reclamação",
    "ouvidoria",
})

# Limites de turnos antes de sugerir encerramento
MAX_TURNS_BEFORE_HINT = 20


def check_force_close(input_lower: str) -> bool:
    """Verifica se deve forçar encerramento."""
    return any(kw in input_lower for kw in FORCE_CLOSE_KEYWORDS)


def check_force_escalation(input_lower: str) -> bool:
    """Verifica se deve forçar escalação."""
    return any(kw in input_lower for kw in FORCE_ESCALATION_KEYWORDS)


def calculate_confidence(
    ai_confidence: float,
    fsm_success: bool,
    force_close: bool,
    force_escalation: bool,
) -> float:
    """Calcula confiança consolidada."""
    if force_close or force_escalation:
        return 1.0  # Regras duras têm 100% de confiança
    if not fsm_success:
        return min(ai_confidence, 0.5)  # Penaliza se FSM falhou
    return ai_confidence


def build_audit_record(
    *,
    session_id: str,
    turn_count: int,
    ai_result: OrchestratorResult,
    fsm_success: bool,
    force_close: bool,
    force_escalation: bool,
    confidence: float,
) -> dict[str, Any]:
    """Constrói registro de auditoria estruturado (sem PII)."""
    # Usa dados dos 4 agentes LLM do OrchestratorResult
    state_result = ai_result.state_suggestion
    response_result = ai_result.response_generation
    message_type_result = ai_result.message_type_selection
    decision_result = ai_result.final_decision

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "session_id": session_id,
        "turn_count": turn_count,
        # StateAgent (LLM #1)
        "state_suggested": (
            state_result.suggested_next_states[0].state
            if state_result.suggested_next_states
            else state_result.current_state
        ),
        "state_confidence": state_result.confidence,
        # ResponseAgent (LLM #2)
        "response_confidence": response_result.confidence,
        # MessageTypeAgent (LLM #3)
        "message_type": message_type_result.message_type,
        "message_type_confidence": message_type_result.confidence,
        # DecisionAgent (LLM #4)
        "final_state": decision_result.final_state,
        "final_message_type": decision_result.final_message_type,
        "understood": decision_result.understood,
        "decision_confidence": decision_result.confidence,
        # Flags de decisão
        "fsm_success": fsm_success,
        "force_close": force_close,
        "force_escalation": force_escalation,
        "overall_confidence": confidence,
        "should_escalate": ai_result.should_escalate,
    }


def determine_final_text(
    *,
    ai_text: str,
    force_close: bool,
    force_escalation: bool,
    turns_exceeded: bool,
    requires_review: bool,
) -> str:
    """Determina texto final da resposta."""
    if force_close:
        return (
            "Entendido! Encerrando nossa conversa. "
            "Obrigado pelo contato e até a próxima!"
        )
    if force_escalation:
        return (
            "Entendo que você precisa falar com um atendente humano. "
            "Estou transferindo sua conversa agora."
        )
    if turns_exceeded and not requires_review:
        return (
            f"{ai_text}\n\nNota: Esta conversa está longa. "
            "Posso ajudar com mais alguma coisa?"
        )
    return ai_text
