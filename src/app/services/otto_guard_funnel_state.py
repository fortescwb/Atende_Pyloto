"""Estado e regras de qualificacao do funil (deterministico).

Separado em arquivo proprio para manter SRP e limite de 200 linhas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.contact_card import ContactCard


def is_already_known(contact_card: ContactCard, question_type: str) -> bool:
    if question_type == "message_volume_per_day":
        return contact_card.message_volume_per_day is not None
    if question_type == "attendants_count":
        return contact_card.attendants_count is not None
    if question_type == "specialists_count":
        return contact_card.specialists_count is not None
    if question_type == "has_crm":
        return contact_card.has_crm is not None or "crm" in contact_card.current_tools
    if question_type == "current_tools":
        return len(contact_card.current_tools) > 0
    if question_type == "full_name":
        return bool(contact_card.full_name)
    if question_type == "email":
        return bool(contact_card.email)
    if question_type == "company":
        return bool(contact_card.company)
    if question_type == "meeting_preferred_datetime_text":
        return bool(contact_card.meeting_preferred_datetime_text)
    if question_type == "users_count":
        return contact_card.users_count is not None
    if question_type == "modules_needed":
        return bool(contact_card.modules_needed)
    if question_type == "desired_features":
        return bool(contact_card.desired_features)
    if question_type == "integrations_needed":
        return bool(contact_card.integrations_needed)
    if question_type == "needs_data_migration":
        return contact_card.needs_data_migration is not None
    return False


def is_relevant_question(contact_card: ContactCard, question_type: str) -> bool:
    """Evita o Otto qualificar automacao quando a vertente nao e automacao."""
    interest = effective_interest(contact_card)

    if question_type in {
        "meeting_preferred_datetime_text",
        "full_name",
        "email",
        "company",
    }:
        return True

    if question_type in _AUTOMATION_QUESTIONS:
        if interest == "automacao_atendimento":
            return True
        need = (contact_card.specific_need or "").lower()
        if any(word in need for word in ("whatsapp", "bot", "chatbot")):
            return True
        return interest in {None, ""}

    if question_type in {"users_count", "modules_needed"}:
        return interest in {"saas", None, ""}

    if question_type in {"desired_features", "integrations_needed", "needs_data_migration"}:
        return interest in {"sob_medida", None, ""}

    return True


def has_minimum_qualification(contact_card: ContactCard) -> bool:
    """Sinais minimos para manter a conversa evoluindo (sem loop)."""
    return ready_to_schedule_meeting(contact_card)


def ready_to_schedule_meeting(contact_card: ContactCard) -> bool:
    if contact_card.meeting_preferred_datetime_text:
        return True

    interest = effective_interest(contact_card)
    has_need = bool(contact_card.specific_need or contact_card.primary_interest)
    if not has_need:
        return False

    if interest == "automacao_atendimento":
        score = _count_true(
            contact_card.message_volume_per_day is not None,
            contact_card.attendants_count is not None,
            _has_crm_or_tools(contact_card),
            bool(contact_card.specific_need),
        )
        return score >= 3
    if interest == "sob_medida":
        score = _count_true(
            bool(contact_card.desired_features),
            bool(contact_card.integrations_needed),
            contact_card.users_count is not None or bool(contact_card.company_size),
        )
        return score >= 2
    if interest == "saas":
        return bool(contact_card.modules_needed) and contact_card.users_count is not None
    if interest == "gestao_perfis_trafego":
        score = _count_true(
            bool(contact_card.specific_need),
            bool(contact_card.budget_indication or contact_card.urgency),
            bool(contact_card.company_size),
        )
        return score >= 2
    if interest == "intermediacao_entregas":
        score = _count_true(
            bool(contact_card.specific_need),
            bool(contact_card.location),
            bool(contact_card.urgency or contact_card.budget_indication),
        )
        return score >= 2
    return bool(contact_card.specific_need)


def effective_interest(contact_card: ContactCard) -> str | None:
    raw = (contact_card.primary_interest or "").strip().lower()
    if not raw:
        return None
    if raw in {"gestao_perfis", "trafego_pago"}:
        return "gestao_perfis_trafego"
    if raw == "intermediacao":
        return "intermediacao_entregas"
    return raw


_AUTOMATION_QUESTIONS = frozenset({
    "message_volume_per_day",
    "attendants_count",
    "specialists_count",
    "has_crm",
    "current_tools",
})


def _has_crm_or_tools(contact_card: ContactCard) -> bool:
    if contact_card.has_crm is not None:
        return True
    return bool(contact_card.current_tools)


def _count_true(*values: bool) -> int:
    return sum(1 for value in values if value)
