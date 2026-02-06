"""Servico do OttoAgent (agente principal)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai.models.otto import OttoDecision, OttoRequest
from ai.prompts.otto_prompt import build_full_prompt
from ai.utils.sanitizer import mask_history

if TYPE_CHECKING:
    from ai.core.otto_client import OttoClientProtocol

logger = logging.getLogger(__name__)

_MAX_HISTORY_MESSAGES = 5

_HANDOFF_TEXT = (
    "Vou conectar voce com nossa equipe para continuar o atendimento. "
    "Aguarde um momento."
)


class OttoAgentService:
    """Servico de decisao do OttoAgent."""

    def __init__(self, client: OttoClientProtocol) -> None:
        self._client = client

    async def decide(self, request: OttoRequest) -> OttoDecision:
        """Executa OttoAgent e retorna decisão bruta (gates externos)."""
        history = mask_history(request.history, max_messages=_MAX_HISTORY_MESSAGES)
        conversation_history = "\n".join(history) if history else "(sem historico)"

        system_prompt, user_prompt = build_full_prompt(
            contact_card_summary=request.contact_card_summary,
            conversation_history=conversation_history,
            session_state=request.session_state,
            valid_transitions=list(request.valid_transitions),
            user_message=request.user_message,
            tenant_intent=request.tenant_intent,
        )

        try:
            decision = await self._client.decide(
                system_prompt=system_prompt,
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

        return decision


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
