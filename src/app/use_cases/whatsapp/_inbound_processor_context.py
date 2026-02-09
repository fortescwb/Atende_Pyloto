"""Mixins de contexto e execução dos agentes inbound."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any

from ai.models.otto import OttoDecision, OttoRequest
from app.use_cases.whatsapp._inbound_helpers import (
    build_tenant_intent,
    get_valid_transitions,
    history_as_strings,
    last_assistant_message,
)
from app.use_cases.whatsapp._inbound_processor_common import _extract_contact_card_signals

if TYPE_CHECKING:
    from app.protocols.models import NormalizedMessage

logger = logging.getLogger(__name__)
_AGENTS_PARALLEL_TIMEOUT_SECONDS = 5.0


class InboundProcessorContextMixin:
    """Métodos de contexto e execução de agentes."""

    @staticmethod
    def _should_skip_message(msg: NormalizedMessage) -> bool:
        message_type = getattr(msg, "message_type", "text")
        raw_text = getattr(msg, "text", None)
        return not msg.from_number or (not raw_text and message_type != "audio")

    async def _resolve_session(self, msg: NormalizedMessage, tenant_id: str) -> Any:
        return await self._session_manager.resolve_or_create(
            sender_id=msg.from_number or "",
            tenant_id=tenant_id,
            whatsapp_name=getattr(msg, "whatsapp_name", None),
        )

    async def _resolve_user_text(
        self,
        *,
        msg: NormalizedMessage,
        session: Any,
        correlation_id: str,
    ) -> tuple[str | None, bool | None]:
        raw_text = getattr(msg, "text", None) or ""
        if getattr(msg, "message_type", "text") != "audio":
            return raw_text, None
        return await self._handle_audio_transcription(
            msg=msg,
            session=session,
            correlation_id=correlation_id,
        )

    async def _prepare_context(
        self,
        msg: NormalizedMessage,
        session: Any,
    ) -> tuple[Any, list[str], str]:
        contact_card = await self._resolve_contact_card(msg, session)
        history = history_as_strings(session)
        summary = contact_card.to_prompt_summary() if contact_card else ""
        return contact_card, history, summary

    async def _run_agents(
        self,
        *,
        session: Any,
        sanitized_input: str,
        history: list[str],
        contact_card: Any,
        card_summary: str,
        raw_user_text: str,
        correlation_id: str,
    ) -> tuple[OttoRequest, OttoDecision, Any]:
        otto_request = self._build_otto_request(
            session=session,
            sanitized_input=sanitized_input,
            history=history,
            card_summary=card_summary,
            correlation_id=correlation_id,
        )
        extraction_task = self._build_extraction_task(
            contact_card=contact_card,
            raw_user_text=raw_user_text,
            assistant_last_message=last_assistant_message(session),
            correlation_id=correlation_id,
        )
        otto_task = self._otto_agent.decide(otto_request)
        if extraction_task:
            try:
                decision, extraction = await asyncio.wait_for(
                    asyncio.gather(otto_task, extraction_task),
                    timeout=_AGENTS_PARALLEL_TIMEOUT_SECONDS,
                )
                return otto_request, decision, extraction
            except TimeoutError:
                logger.warning(
                    "inbound_agents_timeout",
                    extra={
                        "component": "inbound_processor",
                        "action": "run_agents",
                        "result": "timeout_fallback",
                        "correlation_id": correlation_id,
                        "timeout_seconds": _AGENTS_PARALLEL_TIMEOUT_SECONDS,
                    },
                )
                return otto_request, await self._otto_agent.decide(otto_request), None
        return otto_request, await otto_task, None

    async def _validate_decision(
        self,
        decision: OttoDecision,
        otto_request: OttoRequest,
    ) -> OttoDecision:
        validated, result = await self._decision_validator.validate(decision, otto_request)
        if result.corrections:
            with contextlib.suppress(Exception):
                validated = validated.model_copy(update=result.corrections)
        return validated

    def _build_otto_request(
        self,
        *,
        session: Any,
        sanitized_input: str,
        history: list[str],
        card_summary: str,
        correlation_id: str,
    ) -> OttoRequest:
        tenant_intent, intent_confidence = build_tenant_intent(session, sanitized_input)
        loaded_contexts = []
        if getattr(session, "context", None) is not None:
            loaded_contexts = list(getattr(session.context, "prompt_contexts", []) or [])
        return OttoRequest(
            user_message=sanitized_input,
            session_state=session.current_state.name,
            correlation_id=correlation_id,
            history=history,
            contact_card_summary=card_summary,
            contact_card_signals=_extract_contact_card_signals(
                getattr(session, "contact_card", None)
            ),
            tenant_intent=tenant_intent,
            intent_confidence=intent_confidence,
            loaded_contexts=loaded_contexts,
            valid_transitions=list(get_valid_transitions(session.current_state)),
        )

    def _build_extraction_task(
        self,
        *,
        contact_card: Any,
        raw_user_text: str,
        assistant_last_message: str,
        correlation_id: str,
    ) -> Any | None:
        if not self._contact_card_extractor or not contact_card:
            return None
        from ai.models.contact_card_extraction import ContactCardExtractionRequest

        return self._contact_card_extractor.extract(
            ContactCardExtractionRequest(
                user_message=raw_user_text,
                assistant_last_message=assistant_last_message,
                correlation_id=correlation_id,
            )
        )

    async def _resolve_contact_card(self, msg: NormalizedMessage, session: Any) -> Any:
        if self._contact_card_store is None:
            return getattr(session, "contact_card", None)
        contact_card = await self._contact_card_store.get_or_create(
            msg.from_number or "",
            getattr(msg, "whatsapp_name", "") or "",
        )
        session.contact_card = contact_card
        return contact_card
