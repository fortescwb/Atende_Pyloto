"""Servico do OttoAgent (agente principal)."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from ai.models.otto import OttoDecision, OttoRequest
from ai.prompts.otto_prompt import build_full_prompt
from ai.services.prompt_micro_agents import MicroAgentResult, run_prompt_micro_agents
from ai.utils.sanitizer import mask_history
from app.observability import record_confidence, record_handoff, record_latency

if TYPE_CHECKING:
    from ai.core.otto_client import OttoClientProtocol

logger = logging.getLogger(__name__)

_MAX_HISTORY_MESSAGES = 20

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
        start_time = time.perf_counter()
        correlation_id = request.correlation_id
        conversation_history = _conversation_history_text(request.history)
        micro_result = await _safe_run_micro_agents(request, correlation_id)
        system_prompt, user_prompt, loaded_contexts = _build_prompts(
            request=request,
            conversation_history=conversation_history,
            micro_result=micro_result,
        )
        request.loaded_contexts = loaded_contexts
        decision = await self._safe_client_decision(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            correlation_id=correlation_id,
        )
        if decision is not None:
            # P1-2: Registrar latência e confidence
            latency_ms = (time.perf_counter() - start_time) * 1000
            record_latency("otto_agent", "decide", latency_ms, correlation_id)
            record_confidence("otto_agent", "decision", decision.confidence, correlation_id)
            return decision
        logger.warning(
            "otto_client_empty",
            extra={
                "component": "otto_agent",
                "action": "decide_client",
                "result": "empty",
                "correlation_id": correlation_id,
            },
        )
        return _handoff_decision("empty_response", correlation_id=correlation_id)

    async def _safe_client_decision(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        correlation_id: str | None,
    ) -> OttoDecision | None:
        try:
            return await self._client.decide(system_prompt=system_prompt, user_prompt=user_prompt)
        except Exception as exc:
            logger.warning(
                "otto_client_error",
                extra={
                    "component": "otto_agent",
                    "action": "decide_client",
                    "result": "error",
                    "correlation_id": correlation_id,
                    "error_type": type(exc).__name__,
                },
            )
            return _handoff_decision("client_error", correlation_id=correlation_id)


async def _safe_run_micro_agents(
    request: OttoRequest,
    correlation_id: str | None,
) -> MicroAgentResult:
    try:
        return await run_prompt_micro_agents(
            tenant_intent=request.tenant_intent,
            intent_confidence=request.intent_confidence,
            user_message=request.user_message,
            contact_card_signals=request.contact_card_signals,
            session_state=request.session_state,
            correlation_id=correlation_id,
        )
    except Exception as exc:
        logger.warning(
            "micro_agents_error",
            extra={
                "component": "otto_agent",
                "action": "run_micro_agents",
                "result": "error",
                "correlation_id": correlation_id,
                "error_type": type(exc).__name__,
            },
        )
        return MicroAgentResult.empty()


def _build_prompts(
    *,
    request: OttoRequest,
    conversation_history: str,
    micro_result: MicroAgentResult,
) -> tuple[str, str, list[str]]:
    return build_full_prompt(
        contact_card_summary=request.contact_card_summary,
        conversation_history=conversation_history,
        session_state=request.session_state,
        valid_transitions=list(request.valid_transitions),
        user_message=request.user_message,
        tenant_intent=request.tenant_intent,
        intent_confidence=request.intent_confidence,
        loaded_contexts=request.loaded_contexts,
        extra_context_paths=micro_result.context_paths,
        extra_context_chunks=micro_result.context_chunks,
        extra_loaded_contexts=micro_result.loaded_contexts,
        correlation_id=request.correlation_id,
    )


def _conversation_history_text(history: list[str]) -> str:
    normalized = _normalize_history_labels(
        mask_history(history, max_messages=_MAX_HISTORY_MESSAGES)
    )
    return "\n".join(normalized) if normalized else "(sem historico)"


def _handoff_decision(reason: str, *, correlation_id: str | None) -> OttoDecision:
    logger.info(
        "otto_handoff",
        extra={
            "component": "otto_agent",
            "action": "handoff",
            "result": "forced",
            "reason": reason,
            "correlation_id": correlation_id,
        },
    )
    # P1-2: Registrar métrica de handoff
    record_handoff(reason, correlation_id)
    return OttoDecision(
        next_state="HANDOFF_HUMAN",
        response_text=_HANDOFF_TEXT,
        message_type="text",
        confidence=0.0,
        requires_human=True,
        reasoning_debug=reason,
    )


def _normalize_history_labels(history: list[str]) -> list[str]:
    normalized: list[str] = []
    for entry in history:
        text = (entry or "").strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered.startswith(("usu\u00e1rio:", "usuario:")):
            text = f"Usuario: {text.split(':', 1)[1].strip()}"
        elif lowered.startswith(("otto:", "assistente:", "assistant:")):
            text = f"Otto: {text.split(':', 1)[1].strip()}"
        normalized.append(text)
    return normalized
