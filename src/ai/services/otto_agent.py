"""Servico do OttoAgent (agente principal)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai.config.institutional_loader import get_institutional_prompt_section
from ai.models.otto import OttoDecision, OttoRequest
from ai.prompts.otto_prompt import OTTO_SYSTEM_PROMPT, format_otto_prompt
from ai.rules.otto_guardrails import (
    contains_disallowed_pii,
    contains_prohibited_promises,
    is_response_length_valid,
)
from ai.utils.sanitizer import mask_history

if TYPE_CHECKING:
    from ai.core.otto_client import OttoClientProtocol

logger = logging.getLogger(__name__)

_MAX_HISTORY_MESSAGES = 6
_MAX_RESPONSE_CHARS = 500
_CONFIDENCE_APPROVE = 0.85
_CONFIDENCE_ESCALATE = 0.7

_HANDOFF_TEXT = (
    "Vou conectar voce com nossa equipe para continuar o atendimento. "
    "Aguarde um momento."
)


class OttoAgentService:
    """Servico de decisao do OttoAgent."""

    def __init__(self, client: OttoClientProtocol) -> None:
        self._client = client

    async def decide(self, request: OttoRequest) -> OttoDecision:
        """Executa OttoAgent e aplica gate deterministico."""
        institutional_context = get_institutional_prompt_section()
        history = mask_history(request.history, max_messages=_MAX_HISTORY_MESSAGES)
        conversation_history = "\n".join(history) if history else "(sem historico)"

        user_prompt = format_otto_prompt(
            user_message=request.user_message,
            session_state=request.session_state,
            valid_transitions=list(request.valid_transitions),
            institutional_context=institutional_context,
            tenant_context=request.tenant_context,
            contact_card_summary=request.contact_card_summary,
            conversation_history=conversation_history,
        )

        try:
            decision = await self._client.decide(
                system_prompt=OTTO_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
        except Exception as exc:
            logger.warning(
                "otto_client_error",
                extra={"error_type": type(exc).__name__},
            )
            return _handoff_decision("client_error")

        if decision is None:
            logger.warning("otto_client_empty")
            return _handoff_decision("empty_response")

        return _apply_gate(decision, request)


def _apply_gate(decision: OttoDecision, request: OttoRequest) -> OttoDecision:
    if decision.requires_human:
        return _handoff_decision("requires_human_flag")

    if not _is_transition_valid(decision.next_state, request):
        return _handoff_decision("invalid_transition")

    response_text = decision.response_text.strip()
    if not is_response_length_valid(response_text, max_chars=_MAX_RESPONSE_CHARS):
        return _handoff_decision("invalid_response_size")

    if contains_disallowed_pii(response_text):
        return _handoff_decision("pii_detected")

    if contains_prohibited_promises(response_text):
        return _handoff_decision("prohibited_promise")

    if decision.confidence < _CONFIDENCE_ESCALATE:
        return _handoff_decision("low_confidence")

    if decision.confidence < _CONFIDENCE_APPROVE:
        return decision.model_copy(update={"requires_human": True})

    if response_text != decision.response_text:
        return decision.model_copy(update={"response_text": response_text})

    return decision


def _is_transition_valid(next_state: str, request: OttoRequest) -> bool:
    valid_transitions = list(request.valid_transitions)
    if not valid_transitions:
        return next_state == request.session_state
    return next_state in valid_transitions


def _handoff_decision(reason: str) -> OttoDecision:
    logger.info("otto_handoff", extra={"reason": reason})
    return OttoDecision(
        next_state="HANDOFF_HUMAN",
        response_text=_HANDOFF_TEXT,
        message_type="text",
        confidence=0.0,
        requires_human=True,
        reasoning_debug=reason,
    )
