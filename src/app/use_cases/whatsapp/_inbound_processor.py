# EXCECAO REGRA 2.1: fluxo inbound centralizado para manter clareza do pipeline.
"""Processamento detalhado de mensagens inbound (Otto + utilitários)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ai.models.otto import OttoDecision, OttoRequest
from ai.utils.sanitizer import sanitize_pii
from app.use_cases.whatsapp._inbound_helpers import (
    build_outbound_payload,
    build_outbound_request,
    build_tenant_context,
    get_valid_transitions,
    history_as_strings,
    is_terminal_session,
    serialize_contact_card,
)
from fsm.manager import FSMStateMachine
from fsm.states import SessionState

if TYPE_CHECKING:
    from ai.services.contact_card_extractor import ContactCardExtractorService
    from ai.services.otto_agent import OttoAgentService
    from app.protocols import AsyncDedupeProtocol, OutboundSenderProtocol
    from app.protocols.contact_card_store import ContactCardStoreProtocol
    from app.protocols.models import NormalizedMessage
    from app.protocols.session_manager import SessionManagerProtocol
    from app.protocols.transcription_service import TranscriptionServiceProtocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _FallbackDecision:
    response_text: str
    message_type: str = "text"


class InboundMessageProcessor:
    def __init__(
        self,
        *,
        session_manager: SessionManagerProtocol,
        dedupe: AsyncDedupeProtocol,
        otto_agent: OttoAgentService,
        outbound_sender: OutboundSenderProtocol,
        contact_card_store: ContactCardStoreProtocol | None = None,
        transcription_service: TranscriptionServiceProtocol | None = None,
        contact_card_extractor: ContactCardExtractorService | None = None,
    ) -> None:
        self._session_manager = session_manager
        self._dedupe = dedupe
        self._otto_agent = otto_agent
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
        await self._dedupe.mark_processed(msg.message_id)

        session = await self._resolve_session(msg, tenant_id)
        raw_user_text, early_sent = await self._resolve_user_text(
            msg=msg,
            session=session,
            correlation_id=correlation_id,
        )
        if raw_user_text is None:
            return self._build_result(session, bool(early_sent))

        sanitized_input = sanitize_pii(raw_user_text)
        contact_card, history, card_summary, card_serialized = await self._prepare_context(
            msg, session
        )

        decision, extraction = await self._run_agents(
            session=session,
            sanitized_input=sanitized_input,
            history=history,
            contact_card=contact_card,
            card_summary=card_summary,
            card_serialized=card_serialized,
            raw_user_text=raw_user_text,
        )

        if self._contact_card_store and contact_card and extraction:
            await self._apply_contact_card_patch(contact_card, extraction)

        sent = await self._send_response(msg, decision, correlation_id)
        await self._update_session(session, sanitized_input, decision, correlation_id)
        return self._build_result(session, sent)

    @staticmethod
    def _should_skip_message(msg: NormalizedMessage) -> bool:
        message_type = getattr(msg, "message_type", "text")
        raw_text = getattr(msg, "text", None)
        if not msg.from_number:
            return True
        return not raw_text and message_type != "audio"

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
    ) -> tuple[Any, list[str], str, str]:
        contact_card = await self._resolve_contact_card(msg, session)
        history = history_as_strings(session)
        summary = contact_card.to_prompt_summary() if contact_card else ""
        serialized = serialize_contact_card(contact_card)
        return contact_card, history, summary, serialized

    async def _run_agents(
        self,
        *,
        session: Any,
        sanitized_input: str,
        history: list[str],
        contact_card: Any,
        card_summary: str,
        card_serialized: str,
        raw_user_text: str,
    ) -> tuple[OttoDecision, Any]:
        otto_request = self._build_otto_request(
            session=session,
            sanitized_input=sanitized_input,
            history=history,
            card_summary=card_summary,
        )
        extraction_task = self._build_extraction_task(
            contact_card=contact_card,
            raw_user_text=raw_user_text,
            card_serialized=card_serialized,
            history=history,
        )
        otto_task = self._otto_agent.decide(otto_request)
        if extraction_task:
            decision, extraction = await asyncio.gather(otto_task, extraction_task)
            return decision, extraction
        decision = await otto_task
        return decision, None

    def _build_otto_request(
        self,
        *,
        session: Any,
        sanitized_input: str,
        history: list[str],
        card_summary: str,
    ) -> OttoRequest:
        return OttoRequest(
            user_message=sanitized_input,
            session_state=session.current_state.name,
            history=history,
            contact_card_summary=card_summary,
            tenant_context=build_tenant_context(session),
            valid_transitions=list(get_valid_transitions(session.current_state)),
        )

    def _build_extraction_task(
        self,
        *,
        contact_card: Any,
        raw_user_text: str,
        card_serialized: str,
        history: list[str],
    ) -> Any | None:
        if not self._contact_card_extractor or not contact_card:
            return None
        from ai.models.contact_card_extraction import ContactCardExtractionRequest

        return self._contact_card_extractor.extract(
            ContactCardExtractionRequest(
                user_message=raw_user_text,
                contact_card_summary=card_serialized,
                conversation_context=history[-3:] if history else None,
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

    async def _apply_contact_card_patch(self, contact_card: Any, extraction: Any) -> None:
        if not extraction.has_updates:
            return
        from app.services.contact_card_merge import apply_contact_card_patch

        updated = apply_contact_card_patch(contact_card, extraction.updates)
        if updated and self._contact_card_store:
            await self._contact_card_store.upsert(contact_card)
            fields_count = len(extraction.updates.model_dump(exclude_none=True))
            logger.info(
                "contact_card_updated",
                extra={
                    "fields_count": fields_count,
                    "confidence": extraction.confidence,
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
            extra={
                "sent": sent,
                "reason": reason,
                "correlation_id": correlation_id,
            },
        )
        return sent

    async def _update_session(
        self,
        session: Any,
        sanitized_input: str,
        decision: OttoDecision,
        correlation_id: str,
    ) -> None:
        from app.sessions.models import HistoryRole

        self._apply_decision_to_session(session, decision, correlation_id)
        session.add_to_history(sanitized_input, max_history=None)
        if decision.response_text:
            session.add_to_history(
                sanitize_pii(decision.response_text),
                role=HistoryRole.ASSISTANT,
                max_history=None,
            )
        await self._session_manager.save(session)

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
                extra={
                    "correlation_id": correlation_id,
                    "next_state": decision.next_state,
                },
            )
            return

        fsm = FSMStateMachine(
            initial_state=session.current_state,
            session_id=session.session_id,
        )
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
