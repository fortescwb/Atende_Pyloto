"""Escolha deterministica da proxima pergunta / proximo passo.

Separado para manter SRP e limite de 200 linhas.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from api.payload_builders.whatsapp.factory import build_full_payload
from app.protocols.models import OutboundMessageRequest
from app.services.otto_guard_funnel_state import effective_interest, ready_to_schedule_meeting

if TYPE_CHECKING:
    from app.domain.contact_card import ContactCard

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
    for key, text in _build_question_candidates(contact_card):
        if key in skip_fields:
            continue
        if _already_has_value(contact_card, key):
            continue
        return QuestionPick(key=key, text=text)
    return None

async def build_next_step_cta(contact_card: "ContactCard", outbound_sender=None) -> str:
    """
    Sugere próximo passo. Se for hora de agendar, dispara template/flow WhatsApp.
    outbound_sender: OutboundSenderProtocol (injetado pelo pipeline principal)
    """
    if contact_card.meeting_preferred_datetime_text:
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

    if ready_to_schedule_meeting(contact_card):
        # Envia template e flow do WhatsApp
        phone = getattr(contact_card, "wa_id", None) or getattr(contact_card, "phone", None)
        if not phone or not outbound_sender:
            return "Estamos prontos para agendar, mas houve um erro ao acionar o WhatsApp. Por favor, tente novamente mais tarde."
        request = OutboundMessageRequest(
            to=phone,
            message_type="template",
            template_name="agendamento_reuniao",
            template_params=None,  # Template sem parâmetros de body
            language="pt_BR",
            category="MARKETING",
            flow_id="agendamento_reuniao",
            flow_token=phone,  # Usa o número do telefone como token para identificar o usuário
        )
        # Use case já espera validator/builder/sender, mas aqui só chamamos o sender direto para não duplicar lógica
        # O ideal é que o pipeline principal injete o outbound_sender correto
        try:
            # Constrói o payload antes de enviar
            payload = build_full_payload(request)

            # Se for sync, rodar no event loop
            if asyncio.iscoroutinefunction(outbound_sender.send):
                result = await outbound_sender.send(request, payload)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, outbound_sender.send, request, payload)
            if getattr(result, "success", False):
                return "Enviei um link para você agendar sua consultoria pelo WhatsApp. É só seguir as instruções."
            error_msg = getattr(result, "error_message", "Erro desconhecido")
            logger.warning(
                "template_flow_send_failed",
                extra={
                    "to": phone,
                    "error": error_msg,
                    "template_name": "agendamento_reuniao",
                },
            )
            return "Tentei enviar o link de agendamento, mas houve uma falha. Por favor, tente novamente mais tarde."
        except Exception as exc:
            logger.exception(
                "template_flow_send_exception",
                extra={
                    "to": phone,
                    "template_name": "agendamento_reuniao",
                    "error": str(exc),
                },
            )
            return "Tentei enviar o link de agendamento, mas houve uma falha. Por favor, tente novamente mais tarde."

    if contact_card.urgency is None:
        return "Qual a urgencia para colocar isso de pe? (esta semana, este mes, sem pressa)"
    if not contact_card.budget_indication:
        return "Voce ja tem uma faixa de investimento em mente, mesmo que aproximada?"
    return (
        "Se fizer sentido, posso agendar uma conversa rapida de 15 min "
        "para diagnostico/orcamento. Qual melhor dia e horario (seg-sex, 9h-17h)?"
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


def _build_question_candidates(contact_card: ContactCard) -> list[tuple[str, str]]:
    base: list[tuple[str, str]] = []
    if not contact_card.specific_need:
        base.append(("specific_need", "Qual a principal necessidade que voce espera resolver?"))
    interest = effective_interest(contact_card)
    if interest == "automacao_atendimento":
        base.extend(_AUTOMACAO_QUESTIONS)
    elif interest == "sob_medida":
        base.extend(_SOB_MEDIDA_QUESTIONS)
    elif interest == "saas":
        base.extend(_SAAS_QUESTIONS)
    else:
        base.extend(_GENERIC_QUESTIONS)
    return base


_AUTOMACAO_QUESTIONS = [
    ("message_volume_per_day", "Quantas msgs/atendimentos por dia no WhatsApp?"),
    ("attendants_count", "Quantas pessoas atendem essas mensagens hoje?"),
    ("current_tools", "Como voces organizam os atendimentos hoje? (ex: planilha/CRM)"),
    ("specialists_count", "Quantos especialistas receberiam os atendimentos?"),
    ("has_crm", "Voce ja usa algum CRM ou ferramenta para organizar os atendimentos?"),
]

_SOB_MEDIDA_QUESTIONS = [
    ("desired_features", "Quais funcionalidades sao essenciais nesse sistema?"),
    ("integrations_needed", "Precisa integrar com algo? (ERP, WhatsApp, API)"),
    ("needs_data_migration", "Voce precisa migrar dados de planilha/sistema atual?"),
    ("users_count", "Quantas pessoas vao usar o sistema no dia a dia?"),
]

_SAAS_QUESTIONS = [
    ("modules_needed", "Quais modulos voce precisa? (ex: CRM, agenda, financeiro)"),
    ("users_count", "Quantas pessoas vao usar o sistema?"),
    ("current_tools", "Como voces fazem isso hoje? (planilha, WhatsApp, sistema)"),
]

_GENERIC_QUESTIONS = [
    ("urgency", "Qual a urgencia? (esta semana, este mes, sem pressa)"),
    (
        "budget_indication",
        "Voce ja tem uma faixa de investimento (mensal/projeto), mesmo aproximada?",
    ),
]
