"""Escolha deterministica da proxima pergunta / proximo passo.

Separado para manter SRP e limite de 200 linhas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.services.otto_guard_funnel_state import effective_interest, ready_to_schedule_meeting

if TYPE_CHECKING:
    from app.domain.contact_card import ContactCard

@dataclass(frozen=True, slots=True)
class QuestionPick:
    key: str
    text: str


def pick_next_question(
    contact_card: ContactCard,
    *,
    skip_fields: set[str],
) -> QuestionPick | None:
    interest = effective_interest(contact_card)

    base: list[tuple[str, str]] = []
    if not contact_card.specific_need:
        base.append(("specific_need", "Qual a principal necessidade que voce espera resolver?"))

    if interest == "automacao_atendimento":
        base.extend(
            [
                ("message_volume_per_day", "Quantas msgs/atendimentos por dia no WhatsApp?"),
                ("attendants_count", "Quantas pessoas atendem essas mensagens hoje?"),
                ("current_tools", "Como voces organizam os atendimentos hoje? (ex: planilha/CRM)"),
                ("specialists_count", "Quantos especialistas receberiam os atendimentos?"),
                ("has_crm", "Voce ja usa algum CRM ou ferramenta para organizar os atendimentos?"),
            ]
        )
    elif interest == "sob_medida":
        base.extend(
            [
                ("desired_features", "Quais funcionalidades sao essenciais nesse sistema?"),
                ("integrations_needed", "Precisa integrar com algo? (ERP, WhatsApp, API)"),
                ("needs_data_migration", "Voce precisa migrar dados de planilha/sistema atual?"),
                ("users_count", "Quantas pessoas vao usar o sistema no dia a dia?"),
            ]
        )
    elif interest == "saas":
        base.extend(
            [
                ("modules_needed", "Quais modulos voce precisa? (ex: CRM, agenda, financeiro)"),
                ("users_count", "Quantas pessoas vao usar o sistema?"),
                ("current_tools", "Como voces fazem isso hoje? (planilha, WhatsApp, sistema)"),
            ]
        )
    else:
        base.extend(
            [
                ("urgency", "Qual a urgencia? (esta semana, este mes, sem pressa)"),
                (
                    "budget_indication",
                    "Voce ja tem uma faixa de investimento (mensal/projeto), mesmo aproximada?",
                ),
            ]
        )

    for key, text in base:
        if key in skip_fields:
            continue
        if _already_has_value(contact_card, key):
            continue
        return QuestionPick(key=key, text=text)
    return None


def build_next_step_cta(contact_card: ContactCard) -> str:
    """Sugere proximo passo. Retorna string vazia se nao houver."""
    if contact_card.meeting_preferred_datetime_text:
        if not contact_card.email:
            return "Para eu confirmar com o time, qual seu e-mail?"
        if not contact_card.full_name or not contact_card.company:
            missing: list[str] = []
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
        return (
            "Se fizer sentido, posso agendar uma conversa rapida de 15 min "
            "para diagnostico/orcamento. Qual melhor dia e horario (seg-sex, 9h-17h)?"
        )

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
