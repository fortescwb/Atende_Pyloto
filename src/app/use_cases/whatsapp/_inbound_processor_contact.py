"""Mixins de contato, transcrição e respostas fixas do inbound."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from ai.models.contact_card_extraction import ContactCardPatch
from ai.utils.sanitizer import sanitize_pii
from app.services.appointment_handler import save_appointment_from_flow
from app.services.otto_repetition_guard import collect_contact_card_fields
from app.use_cases.whatsapp._inbound_processor_common import _FallbackDecision

if TYPE_CHECKING:
    from app.protocols.models import NormalizedMessage
    from app.services.whatsapp_fixed_replies import FixedReply

logger = logging.getLogger(__name__)


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

    @staticmethod
    def _is_flow_completion_message(msg: NormalizedMessage) -> bool:
        return (
            getattr(msg, "message_type", "") == "interactive"
            and getattr(msg, "interactive_type", "") == "nfm_reply"
            and bool(getattr(msg, "flow_response_json", None))
        )

    async def _handle_flow_completion(
        self,
        *,
        msg: NormalizedMessage,
        session: Any,
        correlation_id: str,
    ) -> None:
        flow_response_json = getattr(msg, "flow_response_json", None)
        appointment = await save_appointment_from_flow(
            flow_response_json=flow_response_json,
            from_number=msg.from_number,
            correlation_id=correlation_id,
            calendar_service=self._calendar_service,
        )
        if appointment and self._contact_card_store and msg.from_number:
            contact_card = await self._contact_card_store.get_or_create(
                msg.from_number,
                getattr(msg, "whatsapp_name", "") or "",
            )
            session.contact_card = contact_card
            patch = _build_contact_card_patch_from_appointment(appointment)
            await self._apply_contact_card_patch(
                contact_card=contact_card,
                patch=patch,
                confidence=1.0,
                correlation_id=correlation_id,
                message_id=msg.message_id,
            )
        await self._append_flow_completion_history(
            session=session,
            flow_response_json=flow_response_json,
        )
        await self._session_manager.save(session)
        log_extra = {
            "component": "inbound_processor",
            "action": "flow_completion",
            "result": "processed",
            "correlation_id": correlation_id,
            "message_id": msg.message_id,
            "saved": bool(appointment),
        }
        if appointment and appointment.get("calendar_event_id"):
            log_extra["calendar_event_id"] = appointment["calendar_event_id"]
        logger.info("flow_completion_processed", extra=log_extra)

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

    async def _append_flow_completion_history(
        self,
        *,
        session: Any,
        flow_response_json: str | None,
    ) -> None:
        from app.sessions.models import HistoryRole

        summary = _flow_completion_summary(flow_response_json)
        session.add_to_history(
            summary,
            role=HistoryRole.SYSTEM,
            max_history=None,
        )


def _build_contact_card_patch_from_appointment(appointment: dict[str, Any]) -> ContactCardPatch:
    date = str(appointment.get("date") or "").strip()
    time = str(appointment.get("time") or "").strip()
    meeting_text = " ".join(item for item in (date, time) if item).strip() or None
    vertical = str(appointment.get("vertical") or "").strip().lower()
    primary_interest = vertical if vertical in {
        "saas",
        "sob_medida",
        "gestao_perfis_trafego",
        "automacao_atendimento",
        "intermediacao_entregas",
    } else None
    return ContactCardPatch(
        full_name=_non_empty(appointment.get("name")),
        email=_non_empty(appointment.get("email")),
        company=_non_empty(appointment.get("company")),
        specific_need=_non_empty(appointment.get("need_description")),
        primary_interest=primary_interest,
        meeting_preferred_datetime_text=meeting_text,
        meeting_mode=_meeting_mode_or_none(appointment.get("meeting_mode")),
    )


def _flow_completion_summary(flow_response_json: str | None) -> str:
    base = "flow_completion_confirmed"
    if not flow_response_json:
        return base
    try:
        payload = json.loads(flow_response_json)
    except (TypeError, ValueError):
        return base
    if not isinstance(payload, dict):
        return base
    params = payload.get("params") if isinstance(payload.get("params"), dict) else payload
    date = _non_empty(params.get("date"))
    time = _non_empty(params.get("time"))
    if date and time:
        return f"flow_completion_confirmed:{date} {time}"
    if date:
        return f"flow_completion_confirmed:{date}"
    return base


def _non_empty(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _meeting_mode_or_none(value: Any) -> str | None:
    mode = (str(value).strip().lower() if value is not None else "")
    if mode in {"online", "presencial"}:
        return mode
    return None
