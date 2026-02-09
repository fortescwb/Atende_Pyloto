# EXCECAO REGRA 2.1: fluxo inbound centralizado para manter clareza do pipeline.
"""Processamento detalhado de mensagens inbound (Otto + utilitários)."""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING, Any

from ai.services.decision_validator import DecisionValidatorService
from ai.utils.sanitizer import sanitize_pii
from app.services.meeting_time_validator import extract_hour, is_within_business_hours
from app.services.otto_repetition_guard import (
    apply_business_hours_guard,
    apply_continuation_guard,
    apply_repetition_guard,
)
from app.services.whatsapp_fixed_replies import match_fixed_reply
from app.use_cases.whatsapp._inbound_processor_contact import InboundProcessorContactMixin
from app.use_cases.whatsapp._inbound_processor_context import InboundProcessorContextMixin
from app.use_cases.whatsapp._inbound_processor_dispatch import InboundProcessorDispatchMixin

if TYPE_CHECKING:
    from ai.models.otto import OttoDecision, OttoRequest
    from ai.services.contact_card_extractor import ContactCardExtractorService
    from ai.services.otto_agent import OttoAgentService
    from app.protocols import AsyncDedupeProtocol, OutboundSenderProtocol
    from app.protocols.contact_card_store import ContactCardStoreProtocol
    from app.protocols.models import NormalizedMessage
    from app.protocols.session_manager import SessionManagerProtocol
    from app.protocols.transcription_service import TranscriptionServiceProtocol

logger = logging.getLogger(__name__)


class InboundMessageProcessor(
    InboundProcessorContextMixin,
    InboundProcessorContactMixin,
    InboundProcessorDispatchMixin,
):
    """Orquestra processamento inbound mantendo compatibilidade do contrato atual."""

    def __init__(
        self,
        *,
        session_manager: SessionManagerProtocol,
        dedupe: AsyncDedupeProtocol,
        otto_agent: OttoAgentService,
        decision_validator: DecisionValidatorService | None = None,
        outbound_sender: OutboundSenderProtocol,
        contact_card_store: ContactCardStoreProtocol | None = None,
        transcription_service: TranscriptionServiceProtocol | None = None,
        contact_card_extractor: ContactCardExtractorService | None = None,
    ) -> None:
        self._session_manager = session_manager
        self._dedupe = dedupe
        self._otto_agent = otto_agent
        self._decision_validator = decision_validator or DecisionValidatorService()
        self._outbound_sender = outbound_sender
        self._contact_card_store = contact_card_store
        self._transcription_service = transcription_service
        self._contact_card_extractor = contact_card_extractor

    async def process(
        self,
        msg: NormalizedMessage,
        correlation_id: str,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        if self._should_skip_message(msg):
            return None
        if await self._dedupe.is_duplicate(msg.message_id):
            return None
        await self._dedupe.mark_processing(msg.message_id)
        try:
            session = await self._resolve_session(msg, tenant_id)
            if self._is_flow_completion_message(msg):
                await self._handle_flow_completion(
                    msg=msg,
                    session=session,
                    correlation_id=correlation_id,
                )
                result = self._build_result(session, False)
                await self._dedupe.mark_processed(msg.message_id)
                return result
            raw_user_text, early_sent = await self._resolve_user_text(
                msg=msg,
                session=session,
                correlation_id=correlation_id,
            )
            if raw_user_text is None:
                result = self._build_result(session, bool(early_sent))
            else:
                sanitized_input = sanitize_pii(raw_user_text)
                fixed_reply = match_fixed_reply(raw_user_text)
                if fixed_reply:
                    sent = await self._send_fixed_reply(msg, fixed_reply, correlation_id)
                    await self._apply_fixed_reply_to_session(
                        session=session,
                        sanitized_input=sanitized_input,
                        fixed_reply=fixed_reply,
                        correlation_id=correlation_id,
                        message_id=msg.message_id,
                    )
                    result = self._build_result(session, sent)
                else:
                    result = await _process_with_agents(
                        self,
                        msg=msg,
                        session=session,
                        sanitized_input=sanitized_input,
                        raw_user_text=raw_user_text,
                        correlation_id=correlation_id,
                    )
            await self._dedupe.mark_processed(msg.message_id)
            return result
        except Exception:
            with contextlib.suppress(Exception):
                await self._dedupe.unmark_processing(msg.message_id)
            raise


async def _process_with_agents(
    processor: InboundMessageProcessor,
    *,
    msg: NormalizedMessage,
    session: Any,
    sanitized_input: str,
    raw_user_text: str,
    correlation_id: str,
) -> dict[str, Any]:
    contact_card, history, card_summary = await processor._prepare_context(msg, session)
    otto_request, decision, extraction = await processor._run_agents(
        session=session,
        sanitized_input=sanitized_input,
        history=history,
        contact_card=contact_card,
        card_summary=card_summary,
        raw_user_text=raw_user_text,
        correlation_id=correlation_id,
    )
    decision = await _post_process_decision(
        processor,
        decision=decision,
        request=otto_request,
        contact_card=contact_card,
        extraction=extraction,
        sanitized_input=sanitized_input,
        correlation_id=correlation_id,
        message_id=msg.message_id,
    )
    sent = await processor._send_response(msg, decision, correlation_id)
    await processor._update_session(
        session,
        sanitized_input,
        decision,
        correlation_id,
        otto_request,
    )
    return processor._build_result(session, sent)


async def _post_process_decision(
    processor: InboundMessageProcessor,
    *,
    decision: OttoDecision,
    request: OttoRequest,
    contact_card: Any,
    extraction: Any,
    sanitized_input: str,
    correlation_id: str,
    message_id: str | None,
) -> OttoDecision:
    extracted_fields = await _apply_extraction(
        processor,
        contact_card=contact_card,
        extraction=extraction,
        correlation_id=correlation_id,
        message_id=message_id,
    )
    guarded = _apply_guards(
        processor,
        decision=decision,
        contact_card=contact_card,
        extracted_fields=extracted_fields,
        user_message=sanitized_input,
        correlation_id=correlation_id,
        message_id=message_id,
    )
    adjusted = processor._maybe_adjust_next_state(
        guarded,
        request,
        contact_card,
        correlation_id,
        message_id,
    )
    return await processor._validate_decision(adjusted, request)


async def _apply_extraction(
    processor: InboundMessageProcessor,
    *,
    contact_card: Any,
    extraction: Any,
    correlation_id: str,
    message_id: str | None,
) -> list[str]:
    if not (contact_card and extraction):
        return []
    patch = extraction.updates
    extracted_fields = list(patch.model_dump(exclude_none=True).keys())
    meeting_text = getattr(patch, "meeting_preferred_datetime_text", None)
    if (
        isinstance(meeting_text, str)
        and meeting_text.strip()
        and is_within_business_hours(meeting_text) is False
    ):
        logger.info(
            "meeting_time_out_of_business_hours",
            extra={
                "component": "meeting_policy",
                "action": "validate_time",
                "result": "rejected",
                "correlation_id": correlation_id,
                "message_id": message_id,
                "hour": extract_hour(meeting_text),
            },
        )
        patch = patch.model_copy(update={"meeting_preferred_datetime_text": None})
        extracted_fields = list({*extracted_fields, "meeting_time_out_of_hours"})
    await processor._apply_contact_card_patch(
        contact_card=contact_card,
        patch=patch,
        confidence=float(getattr(extraction, "confidence", 0.0) or 0.0),
        correlation_id=correlation_id,
        message_id=message_id,
    )
    return extracted_fields


def _apply_guards(
    processor: InboundMessageProcessor,
    *,
    decision: OttoDecision,
    contact_card: Any,
    extracted_fields: list[str],
    user_message: str,
    correlation_id: str,
    message_id: str | None,
) -> OttoDecision:
    if not contact_card:
        return decision
    processor._log_contact_card_snapshot(
        contact_card=contact_card,
        correlation_id=correlation_id,
        message_id=message_id,
    )
    business_hours_decision = _apply_business_hours_guard_log(
        decision=decision,
        extracted_fields=extracted_fields,
        correlation_id=correlation_id,
        message_id=message_id,
    )
    if business_hours_decision is not None:
        return business_hours_decision
    return _apply_repetition_and_continuation_guards(
        decision=decision,
        contact_card=contact_card,
        extracted_fields=extracted_fields,
        user_message=user_message,
        correlation_id=correlation_id,
        message_id=message_id,
    )


def _apply_business_hours_guard_log(
    *,
    decision: OttoDecision,
    extracted_fields: list[str],
    correlation_id: str,
    message_id: str | None,
) -> OttoDecision | None:
    business_hours = apply_business_hours_guard(decision=decision, recent_fields=extracted_fields)
    if not business_hours.applied:
        return None
    return _log_guard_and_get_decision(
        guard_name="otto_business_hours_guard_applied",
        decision=business_hours.decision,
        correlation_id=correlation_id,
        message_id=message_id,
        metadata={"guard_type": business_hours.guard_type},
    )


def _apply_repetition_and_continuation_guards(
    *,
    decision: OttoDecision,
    contact_card: Any,
    extracted_fields: list[str],
    user_message: str,
    correlation_id: str,
    message_id: str | None,
) -> OttoDecision:
    repetition = apply_repetition_guard(
        decision=decision,
        contact_card=contact_card,
        recent_fields=extracted_fields,
    )
    if repetition.applied:
        return _log_guard_and_get_decision(
            guard_name="otto_repetition_guard_applied",
            decision=repetition.decision,
            correlation_id=correlation_id,
            message_id=message_id,
            metadata={
                "question_type": repetition.question_type,
                "next_question_key": repetition.next_question_key,
                "guard_type": repetition.guard_type,
            },
        )
    continuation = apply_continuation_guard(
        decision=decision,
        contact_card=contact_card,
        user_message=user_message,
        recent_fields=extracted_fields,
    )
    if continuation.applied:
        return _log_guard_and_get_decision(
            guard_name="otto_continuation_guard_applied",
            decision=continuation.decision,
            correlation_id=correlation_id,
            message_id=message_id,
            metadata={
                "guard_type": continuation.guard_type,
                "next_question_key": continuation.next_question_key,
            },
        )
    return decision


def _log_guard_and_get_decision(
    *,
    guard_name: str,
    decision: OttoDecision,
    correlation_id: str,
    message_id: str | None,
    metadata: dict[str, Any],
) -> OttoDecision:
    logger.info(
        guard_name,
        extra={
            "component": "otto_guard",
            "action": "guard_applied",
            "result": "response_updated",
            "correlation_id": correlation_id,
            "message_id": message_id,
            **metadata,
        },
    )
    return decision
