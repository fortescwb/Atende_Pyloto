"""Escolha deterministica da proxima pergunta / proximo passo."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from api.payload_builders.whatsapp.factory import build_full_payload
from app.protocols.models import OutboundMessageRequest
from app.services.otto_guard_funnel_question_candidates import build_question_candidates
from app.services.otto_guard_funnel_state import ready_to_schedule_meeting

if TYPE_CHECKING:
    from app.domain.contact_card import ContactCard
    from app.protocols.calendar_service import CalendarServiceProtocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class QuestionPick:
    key: str
    text: str


def pick_next_question(
    contact_card: ContactCard,
    *,
    skip_fields: set[str],
) -> QuestionPick | None:
    for key, text in build_question_candidates(contact_card):
        if key in skip_fields:
            continue
        if _already_has_value(contact_card, key):
            continue
        return QuestionPick(key=key, text=text)
    return None


async def build_next_step_cta(
    contact_card: ContactCard,
    outbound_sender: Any = None,
    calendar_service: CalendarServiceProtocol | None = None,
) -> str:
    """Sugere proximo passo e dispara flow de agendamento quando apropriado."""
    if contact_card.meeting_preferred_datetime_text:
        return _build_meeting_details_message(contact_card)

    if ready_to_schedule_meeting(contact_card):
        phone = getattr(contact_card, "wa_id", None) or getattr(contact_card, "phone", None)
        if not phone or not outbound_sender:
            return _SCHEDULE_SEND_ERROR_MESSAGE
        if calendar_service is not None:
            try:
                has_slots = await _has_available_slots(calendar_service)
            except Exception:
                logger.exception(
                    "calendar_availability_check_failed",
                    extra={
                        "component": "otto_guard",
                        "action": "check_calendar_availability",
                        "result": "error",
                        "correlation_id": None,
                    },
                )
                has_slots = True
            if not has_slots:
                return _FULL_CALENDAR_MESSAGE
        sent = await _send_schedule_template(phone=phone, outbound_sender=outbound_sender)
        return _SCHEDULE_SENT_MESSAGE if sent else _SCHEDULE_SEND_FAILURE_MESSAGE

    if contact_card.urgency is None:
        return "Qual a urgencia para colocar isso de pe? (esta semana, este mes, sem pressa)"
    if not contact_card.budget_indication:
        return "Voce ja tem uma faixa de investimento em mente, mesmo que aproximada?"
    return (
        "Se fizer sentido, posso agendar uma conversa rapida de 15 min "
        "para diagnostico/orcamento. Qual melhor dia e horario (seg-sex, 9h-17h)?"
    )


async def _has_available_slots(calendar_service: CalendarServiceProtocol) -> bool:
    """Consulta agenda em 5 dias uteis para evitar envio de CTA invalido."""
    base = datetime.now(tz=UTC)
    checked_days = 0
    day_offset = 0
    while checked_days < 5:
        day_offset += 1
        candidate = base + timedelta(days=day_offset)
        if candidate.weekday() >= 5:
            continue
        checked_days += 1
        date_str = candidate.strftime("%Y-%m-%d")
        slots = await calendar_service.check_availability(date_str)
        if any(slot.available for slot in slots):
            return True
    return False


async def _send_schedule_template(*, phone: str, outbound_sender: Any) -> bool:
    request = OutboundMessageRequest(
        to=phone,
        message_type="template",
        template_name="agendamento_reuniao",
        template_params=None,
        language="pt_BR",
        category="MARKETING",
        flow_id="agendamento_reuniao",
        flow_token=phone,
    )
    payload = build_full_payload(request)
    try:
        if asyncio.iscoroutinefunction(outbound_sender.send):
            result = await outbound_sender.send(request, payload)
        else:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, outbound_sender.send, request, payload)
    except Exception:
        logger.exception(
            "template_flow_send_exception",
            extra={
                "component": "otto_guard",
                "action": "send_template_flow",
                "result": "error",
                "correlation_id": None,
            },
        )
        return False

    success = bool(getattr(result, "success", False))
    if not success:
        logger.warning(
            "template_flow_send_failed",
            extra={
                "component": "otto_guard",
                "action": "send_template_flow",
                "result": "error",
                "correlation_id": None,
                "template_name": "agendamento_reuniao",
            },
        )
    return success


def _build_meeting_details_message(contact_card: ContactCard) -> str:
    if not contact_card.email:
        return "Para eu confirmar com o time, qual seu e-mail?"
    if not contact_card.full_name or not contact_card.company:
        missing = []
        if not contact_card.full_name:
            missing.append("seu nome completo")
        if not contact_card.company:
            missing.append("o nome do escritorio/empresa")
        joined = " e ".join(missing)
        return f"Para eu registrar certinho, pode me dizer {joined}?"
    return (
        "Perfeito. Vou passar isso para o time da Pyloto confirmar o agendamento "
        "e te chamar por aqui."
    )


def _already_has_value(contact_card: ContactCard, key: str) -> bool:
    if key == "message_volume_per_day":
        return contact_card.message_volume_per_day is not None
    if key == "attendants_count":
        return contact_card.attendants_count is not None
    if key == "specialists_count":
        return contact_card.specialists_count is not None
    if key == "current_tools":
        return bool(contact_card.current_tools)
    if key == "has_crm":
        return contact_card.has_crm is not None or "crm" in contact_card.current_tools
    if key == "desired_features":
        return bool(contact_card.desired_features)
    if key == "integrations_needed":
        return bool(contact_card.integrations_needed)
    if key == "needs_data_migration":
        return contact_card.needs_data_migration is not None
    if key == "users_count":
        return contact_card.users_count is not None
    if key == "modules_needed":
        return bool(contact_card.modules_needed)
    if key == "urgency":
        return contact_card.urgency is not None
    if key == "budget_indication":
        return bool(contact_card.budget_indication)
    if key == "specific_need":
        return bool(contact_card.specific_need)
    return False


_FULL_CALENDAR_MESSAGE = "Nosso time esta com a agenda cheia no momento. Vamos entrar em contato assim que liberar um horario."  # noqa: E501
_SCHEDULE_SENT_MESSAGE = "Enviei um link para voce agendar sua consultoria pelo WhatsApp. E so seguir as instrucoes."  # noqa: E501
_SCHEDULE_SEND_ERROR_MESSAGE = "Estamos prontos para agendar, mas houve um erro ao acionar o WhatsApp. Por favor, tente novamente mais tarde."  # noqa: E501
_SCHEDULE_SEND_FAILURE_MESSAGE = "Tentei enviar o link de agendamento, mas houve uma falha. Por favor, tente novamente mais tarde."  # noqa: E501
