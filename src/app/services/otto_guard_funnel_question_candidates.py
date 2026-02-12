"""Candidatos de perguntas para o funil de qualificacao."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.otto_guard_funnel_state import effective_interest

if TYPE_CHECKING:
    from app.domain.contact_card import ContactCard

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


def build_question_candidates(contact_card: ContactCard) -> list[tuple[str, str]]:
    """Centraliza a selecao para manter consistencia entre guards e CTA."""
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
