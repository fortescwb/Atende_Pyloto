"""Mixins de atualização de sessão, FSM e envio outbound."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ai.utils.sanitizer import sanitize_pii
from app.use_cases.whatsapp._inbound_helpers import (
    build_outbound_payload,
    build_outbound_request,
    is_terminal_session,
)
from app.use_cases.whatsapp._inbound_processor_state_adjustments import (
    adjust_for_meeting_collected,
    adjust_for_meeting_question,
)
from fsm.manager import FSMStateMachine
from fsm.states import SessionState

if TYPE_CHECKING:
    from ai.models.otto import OttoDecision, OttoRequest
    from app.protocols.models import NormalizedMessage

logger = logging.getLogger(__name__)


class InboundProcessorDispatchMixin:
    """Métodos de atualização de sessão, state machine e envio outbound."""

    async def _update_session(
        self,
        session: Any,
        sanitized_input: str,
        decision: OttoDecision,
        correlation_id: str,
        otto_request: OttoRequest,
    ) -> None:
        from app.sessions.models import HistoryRole, SessionContext

        self._apply_decision_to_session(session, decision, correlation_id)
        if getattr(session, "context", None) is not None:
            current = session.context
            prompt_vertical = (
                str(otto_request.tenant_intent)
                if otto_request.tenant_intent
                else current.prompt_vertical
            )
            session.context = SessionContext(
                tenant_id=current.tenant_id,
                vertente=current.vertente,
                rules=current.rules,
                limits=current.limits,
                prompt_vertical=prompt_vertical,
                prompt_contexts=list(otto_request.loaded_contexts or []),
            )
        session.add_to_history(sanitized_input, max_history=None)
        if decision.response_text:
            session.add_to_history(
                sanitize_pii(decision.response_text),
                role=HistoryRole.ASSISTANT,
                max_history=None,
            )
        await self._session_manager.save(session)

    def _maybe_adjust_next_state(
        self,
        decision: OttoDecision,
        request: OttoRequest,
        contact_card: Any,
        correlation_id: str,
        message_id: str | None,
    ) -> OttoDecision:
        valid = set(request.valid_transitions or [])
        text = (decision.response_text or "").lower()
        adjusted = adjust_for_meeting_question(
            decision=decision,
            valid=valid,
            text=text,
            correlation_id=correlation_id,
            message_id=message_id,
        )
        return adjusted or adjust_for_meeting_collected(
            decision=decision,
            valid=valid,
            text=text,
            contact_card=contact_card,
            correlation_id=correlation_id,
            message_id=message_id,
        ) or decision

    def _apply_decision_to_session(
        self,
        session: Any,
        decision: OttoDecision,
        correlation_id: str,
    ) -> None:
        try:
            target_state = SessionState[decision.next_state]
        except KeyError:
            logger.warning(
                "invalid_otto_next_state",
                extra={"correlation_id": correlation_id, "next_state": decision.next_state},
            )
            return
        fsm = FSMStateMachine(initial_state=session.current_state, session_id=session.session_id)
        result = fsm.transition(
            target=target_state,
            trigger="otto_decision",
            metadata={"correlation_id": correlation_id},
            confidence=decision.confidence,
        )
        if result.success and result.transition:
            session.transition_to(result.transition.to_state)

    async def _send_response(
        self,
        msg: NormalizedMessage,
        decision: Any,
        correlation_id: str,
    ) -> bool:
        try:
            request = build_outbound_request(msg, decision, correlation_id)
            recipient = msg.from_number or ""
            if recipient and not recipient.startswith("+"):
                recipient = f"+{recipient}"
            payload = build_outbound_payload(
                decision,
                recipient,
                reply_to_message_id=msg.message_id,
            )
            response = await self._outbound_sender.send(request, payload)
            return response.success
        except Exception as exc:
            logger.error(
                "outbound_send_failed",
                extra={
                    "correlation_id": correlation_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return False

    @staticmethod
    def _build_result(session: Any, sent: bool) -> dict[str, Any]:
        return {
            "session_id": session.session_id,
            "final_state": session.current_state.name,
            "closed": is_terminal_session(session),
            "sent": sent,
        }
