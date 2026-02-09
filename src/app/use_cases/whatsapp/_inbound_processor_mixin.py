"""Mixins auxiliares do processamento inbound WhatsApp."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ai.models.otto import OttoDecision, OttoRequest
from ai.utils.sanitizer import sanitize_pii
from app.services.meeting_time_validator import extract_hour, is_within_business_hours
from app.services.otto_repetition_guard import (
    apply_business_hours_guard,
    apply_continuation_guard,
    apply_repetition_guard,
    collect_contact_card_fields,
)
from app.services.whatsapp_fixed_replies import FixedReply
from app.use_cases.whatsapp._inbound_helpers import (
    build_outbound_payload,
    build_outbound_request,
    build_tenant_intent,
    get_valid_transitions,
    history_as_strings,
    is_terminal_session,
    last_assistant_message,
)
from fsm.manager import FSMStateMachine
from fsm.states import SessionState

if TYPE_CHECKING:
    from app.protocols.models import NormalizedMessage

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _FallbackDecision:
    response_text: str
    message_type: str = "text"


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
            decision, extraction = await asyncio.gather(otto_task, extraction_task)
            return otto_request, decision, extraction
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
            contact_card_signals=_extract_contact_card_signals(getattr(session, "contact_card", None)),
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


class InboundProcessorContactMixin:
    """Métodos de patch de contato, transcrição e respostas fixas."""

    async def _apply_contact_card_patch(
        self,
        *,
        contact_card: Any,
        patch: Any,
        confidence: float,
        correlation_id: str,
        message_id: str | None,
    ) -> None:
        data = patch.model_dump(exclude_none=True) if patch is not None else {}
        if not data:
            return
        from app.services.contact_card_merge import apply_contact_card_patch

        updated = apply_contact_card_patch(contact_card, patch)
        if updated and self._contact_card_store:
            await self._contact_card_store.upsert(contact_card)
            extracted_fields = list(data.keys())
            logger.info(
                "contact_card_updated",
                extra={
                    "component": "inbound_processor",
                    "action": "contact_card_update",
                    "result": "updated",
                    "correlation_id": correlation_id,
                    "message_id": message_id,
                    "fields_count": len(extracted_fields),
                    "extracted_fields": extracted_fields,
                    "confidence": confidence,
                },
            )

    def _log_contact_card_snapshot(
        self,
        *,
        contact_card: Any,
        correlation_id: str,
        message_id: str | None,
    ) -> None:
        logger.info(
            "contact_card_snapshot",
            extra={
                "component": "inbound_processor",
                "action": "contact_card_snapshot",
                "result": "ok",
                "correlation_id": correlation_id,
                "message_id": message_id,
                "fields_present": collect_contact_card_fields(contact_card),
            },
        )

    async def _handle_audio_transcription(
        self,
        *,
        msg: NormalizedMessage,
        session: Any,
        correlation_id: str,
    ) -> tuple[str | None, bool | None]:
        if not self._transcription_service:
            sent = await self._respond_transcription_failure(
                msg=msg,
                session=session,
                correlation_id=correlation_id,
                reason="service_unavailable",
            )
            return None, sent
        transcription = await self._transcription_service.transcribe_whatsapp_audio(
            media_id=getattr(msg, "media_id", None),
            media_url=getattr(msg, "media_url", None),
            mime_type=getattr(msg, "media_mime_type", None),
            wa_id=msg.from_number or "",
        )
        if transcription.confidence < 0.6 or not transcription.text:
            sent = await self._respond_transcription_failure(
                msg=msg,
                session=session,
                correlation_id=correlation_id,
                reason="low_confidence",
            )
            return None, sent
        return transcription.text, None

    async def _respond_transcription_failure(
        self,
        *,
        msg: NormalizedMessage,
        session: Any,
        correlation_id: str,
        reason: str,
    ) -> bool:
        from app.sessions.models import HistoryRole

        decision = _FallbackDecision(
            response_text="Nao consegui entender o audio. Pode enviar em texto, por favor?",
            message_type="text",
        )
        sent = await self._send_response(msg, decision, correlation_id)
        session.add_to_history("audio_nao_compreendido", max_history=None)
        session.add_to_history(
            sanitize_pii(decision.response_text),
            role=HistoryRole.ASSISTANT,
            max_history=None,
        )
        await self._session_manager.save(session)
        logger.info(
            "transcription_fallback_sent",
            extra={"sent": sent, "reason": reason, "correlation_id": correlation_id},
        )
        return sent

    async def _send_fixed_reply(
        self,
        msg: NormalizedMessage,
        fixed_reply: FixedReply,
        correlation_id: str,
    ) -> bool:
        decision = _FallbackDecision(
            response_text=fixed_reply.response_text,
            message_type=fixed_reply.message_type,
        )
        return await self._send_response(msg, decision, correlation_id)

    async def _apply_fixed_reply_to_session(
        self,
        *,
        session: Any,
        sanitized_input: str,
        fixed_reply: FixedReply,
        correlation_id: str,
        message_id: str | None,
    ) -> None:
        from app.sessions.models import HistoryRole, SessionContext

        session.add_to_history(sanitized_input, role=HistoryRole.USER, max_history=None)
        session.add_to_history(
            sanitize_pii(fixed_reply.response_text),
            role=HistoryRole.ASSISTANT,
            max_history=None,
        )
        if fixed_reply.prompt_vertical and getattr(session, "context", None) is not None:
            current = session.context
            session.context = SessionContext(
                tenant_id=current.tenant_id,
                vertente=current.vertente,
                rules=current.rules,
                limits=current.limits,
                prompt_vertical=fixed_reply.prompt_vertical,
                prompt_contexts=list(current.prompt_contexts or []),
            )
        await self._session_manager.save(session)
        logger.info(
            "fixed_reply_applied",
            extra={
                "component": "inbound_processor",
                "action": "fixed_reply",
                "result": "sent",
                "correlation_id": correlation_id,
                "message_id": message_id,
                "reply_key": fixed_reply.key,
                "reply_kind": fixed_reply.kind,
            },
        )


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
            prompt_vertical = str(otto_request.tenant_intent) if otto_request.tenant_intent else current.prompt_vertical
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
        adjusted = _adjust_for_meeting_question(
            decision=decision,
            valid=valid,
            text=text,
            correlation_id=correlation_id,
            message_id=message_id,
        )
        return adjusted or _adjust_for_meeting_collected(
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
            payload = build_outbound_payload(decision, recipient, reply_to_message_id=msg.message_id)
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


def _extract_contact_card_signals(contact_card: Any) -> dict[str, str]:
    if contact_card is None:
        return {}
    signals: dict[str, str] = {}
    for key in ("company_size", "budget_indication", "specific_need", "company", "role"):
        value = getattr(contact_card, key, None)
        if isinstance(value, str) and value.strip():
            signals[key] = value.strip()
    return signals


def _adjust_for_meeting_question(
    *,
    decision: OttoDecision,
    valid: set[str],
    text: str,
    correlation_id: str,
    message_id: str | None,
) -> OttoDecision | None:
    asks_meeting_time = (
        ("agendar" in text and "?" in text)
        or "qual melhor dia" in text
        or "dia e horario" in text
        or "dia/hor" in text
    )
    if not (asks_meeting_time and "COLLECTING_INFO" in valid and decision.next_state != "COLLECTING_INFO"):
        return None
    logger.info(
        "otto_next_state_adjusted",
        extra={
            "component": "otto_guard",
            "action": "adjust_next_state",
            "result": "updated",
            "correlation_id": correlation_id,
            "message_id": message_id,
            "from_state": decision.next_state,
            "to_state": "COLLECTING_INFO",
            "reason": "asking_meeting_time",
        },
    )
    return decision.model_copy(update={"next_state": "COLLECTING_INFO"})


def _adjust_for_meeting_collected(
    *,
    decision: OttoDecision,
    valid: set[str],
    text: str,
    contact_card: Any,
    correlation_id: str,
    message_id: str | None,
) -> OttoDecision | None:
    meeting_text = getattr(contact_card, "meeting_preferred_datetime_text", None)
    email = getattr(contact_card, "email", None)
    should_close = bool(meeting_text) and bool(email) and "?" not in text
    if not should_close:
        return None
    if "SCHEDULED_FOLLOWUP" not in valid or decision.next_state == "SCHEDULED_FOLLOWUP":
        return None
    logger.info(
        "otto_next_state_adjusted",
        extra={
            "component": "otto_guard",
            "action": "adjust_next_state",
            "result": "updated",
            "correlation_id": correlation_id,
            "message_id": message_id,
            "from_state": decision.next_state,
            "to_state": "SCHEDULED_FOLLOWUP",
            "reason": "meeting_collected",
        },
    )
    return decision.model_copy(update={"next_state": "SCHEDULED_FOLLOWUP"})
