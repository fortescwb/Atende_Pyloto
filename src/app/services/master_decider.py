"""Decisor Mestre — governança final de decisões.

Consolida saídas da FSM, resposta gerada e regras de encerramento.
Integra com DecisionAgentResult (LLM #4) do pipeline de 4 agentes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.services._decider_helpers import (
    MAX_TURNS_BEFORE_HINT,
    build_audit_record,
    calculate_confidence,
    check_force_close,
    check_force_escalation,
    determine_final_text,
)

if TYPE_CHECKING:
    from ai.services.orchestrator import OrchestratorResult
    from app.sessions.models import Session
    from fsm.types import TransitionResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MasterDecision:
    """Decisão consolidada do decisor mestre."""

    final_text: str
    final_message_type: str
    final_state: str
    understood: bool = True
    should_close_session: bool = False
    close_reason: str | None = None
    requires_human_escalation: bool = False
    audit_record: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.8


class MasterDecider:
    """Decisor mestre para governança final."""

    def decide(
        self,
        *,
        session: Session,
        ai_result: OrchestratorResult,
        fsm_result: TransitionResult,
        user_input: str,
    ) -> MasterDecision:
        """Toma decisão consolidada integrando DecisionAgent (LLM #4)."""
        input_lower = user_input.lower()

        force_close = check_force_close(input_lower)
        force_escalation = check_force_escalation(input_lower)
        turns_exceeded = session.turn_count >= MAX_TURNS_BEFORE_HINT

        # Usa texto do DecisionAgent (LLM #4) como base
        decision = ai_result.final_decision
        ai_text = decision.final_text
        understood = decision.understood

        final_text = determine_final_text(
            ai_text=ai_text,
            force_close=force_close,
            force_escalation=force_escalation,
            turns_exceeded=turns_exceeded,
            requires_review=not understood,
        )

        # Estado: prioriza DecisionAgent, fallback para FSM
        final_state = decision.final_state
        if fsm_result.success and fsm_result.transition:
            final_state = fsm_result.transition.to_state.name

        # Tipo de mensagem do DecisionAgent
        final_message_type = decision.final_message_type
        if force_close or force_escalation:
            final_message_type = "text"

        should_close = force_close or session.is_terminal
        needs_escalation = (
            force_escalation
            or ai_result.should_escalate
            or decision.should_escalate
            or ai_result.response_generation.requires_human_review
        )

        confidence = calculate_confidence(
            ai_result.overall_confidence,
            fsm_result.success,
            force_close,
            force_escalation,
        )

        audit_record = build_audit_record(
            session_id=session.session_id,
            turn_count=session.turn_count,
            ai_result=ai_result,
            fsm_success=fsm_result.success,
            force_close=force_close,
            force_escalation=force_escalation,
            confidence=confidence,
        )

        logger.info(
            "master_decision_made",
            extra={
                "session_id": session.session_id,
                "final_state": final_state,
                "understood": understood,
                "should_close": should_close,
                "needs_escalation": needs_escalation,
                "confidence": confidence,
            },
        )

        return MasterDecision(
            final_text=final_text,
            final_message_type=final_message_type,
            final_state=final_state,
            understood=understood,
            should_close_session=should_close,
            close_reason="user_request" if force_close else None,
            requires_human_escalation=needs_escalation,
            audit_record=audit_record,
            confidence=confidence,
        )
