"""Guard deterministico para evitar perguntas repetidas do Otto."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ai.models.otto import OttoDecision
from app.domain.contact_card import ContactCard


@dataclass(frozen=True, slots=True)
class GuardResult:
    decision: OttoDecision
    applied: bool
    question_type: str | None = None
    next_question_key: str | None = None


@dataclass(frozen=True, slots=True)
class QuestionPick:
    key: str
    text: str


def apply_repetition_guard(
    *,
    decision: OttoDecision,
    contact_card: ContactCard | None,
) -> GuardResult:
    """Evita repetir pergunta quando o dado ja existe no ContactCard."""
    if contact_card is None:
        return GuardResult(decision=decision, applied=False)
    response_text = (decision.response_text or "").strip()
    if not response_text:
        return GuardResult(decision=decision, applied=False)

    question_type = _detect_question_type(response_text)
    if question_type is None:
        return GuardResult(decision=decision, applied=False)

    if not _is_already_known(contact_card, question_type):
        return GuardResult(decision=decision, applied=False)

    ack = _build_ack(contact_card, question_type)
    next_pick = _pick_next_question(contact_card, skip_fields={question_type})
    replacement = _combine_ack_and_question(ack, next_pick.text if next_pick else "")
    updated = decision.model_copy(update={"response_text": replacement})
    return GuardResult(
        decision=updated,
        applied=True,
        question_type=question_type,
        next_question_key=next_pick.key if next_pick else None,
    )


def collect_contact_card_fields(contact_card: ContactCard | None) -> list[str]:
    """Retorna lista de campos nao sensiveis presentes no ContactCard."""
    if contact_card is None:
        return []
    fields: list[str] = []
    if contact_card.primary_interest:
        fields.append("primary_interest")
    if contact_card.secondary_interests:
        fields.append("secondary_interests")
    if contact_card.urgency:
        fields.append("urgency")
    if contact_card.budget_indication:
        fields.append("budget_indication")
    if contact_card.specific_need:
        fields.append("specific_need")
    if contact_card.company_size:
        fields.append("company_size")
    if contact_card.message_volume_per_day is not None:
        fields.append("message_volume_per_day")
    if contact_card.attendants_count is not None:
        fields.append("attendants_count")
    if contact_card.specialists_count is not None:
        fields.append("specialists_count")
    if contact_card.has_crm is not None:
        fields.append("has_crm")
    if contact_card.current_tools:
        fields.append("current_tools")
    return fields


def _detect_question_type(text: str) -> str | None:
    normalized = text.lower()
    if not _looks_like_question(normalized):
        return None

    if _contains_any(normalized, _MESSAGE_VOLUME_KEYWORDS):
        return "message_volume_per_day"
    if _contains_any(normalized, _ATTENDANTS_KEYWORDS):
        return "attendants_count"
    if _contains_any(normalized, _SPECIALISTS_KEYWORDS):
        return "specialists_count"
    if _contains_any(normalized, _CRM_KEYWORDS):
        return "has_crm"
    if _contains_any(normalized, _TOOLS_KEYWORDS):
        return "current_tools"
    return None


def _looks_like_question(text: str) -> bool:
    if "?" in text:
        return True
    starts = ("qual ", "quais ", "quant", "voce ", "ja ", "tem ", "usa ")
    return text.strip().startswith(starts)


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _is_already_known(contact_card: ContactCard, question_type: str) -> bool:
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
    return False


def _build_ack(contact_card: ContactCard, question_type: str) -> str:
    if question_type == "message_volume_per_day":
        volume = contact_card.message_volume_per_day
        return f"Entendi, voce recebe cerca de {volume} mensagens por dia."
    if question_type == "attendants_count":
        attendants = contact_card.attendants_count
        return f"Entendi, sao {attendants} pessoas atendendo hoje."
    if question_type == "specialists_count":
        specialists = contact_card.specialists_count
        return f"Entendi, {specialists} especialistas recebem os atendimentos."
    if question_type == "has_crm":
        has_crm = contact_card.has_crm
        if has_crm is True or "crm" in contact_card.current_tools:
            return "Entendi, voce ja usa CRM."
        return "Entendi, voce ainda nao usa CRM."
    if question_type == "current_tools":
        tools = _format_tools(contact_card.current_tools)
        return f"Entendi, hoje voces usam {tools}."
    return "Entendi."


def _pick_next_question(
    contact_card: ContactCard,
    *,
    skip_fields: set[str],
) -> QuestionPick | None:
    candidates: list[tuple[str, Callable[[ContactCard], bool], str]] = [
        (
            "specific_need",
            lambda card: not card.specific_need,
            "Qual a principal necessidade que voce espera desse bot?",
        ),
        (
            "has_crm",
            lambda card: card.has_crm is None and "crm" not in card.current_tools,
            "Voce ja usa algum CRM ou ferramenta para organizar os atendimentos?",
        ),
        (
            "current_tools",
            lambda card: not card.current_tools,
            "Como voces organizam os atendimentos hoje? (ex: planilha/CRM)",
        ),
        (
            "attendants_count",
            lambda card: card.attendants_count is None,
            "Quantas pessoas atendem o WhatsApp hoje?",
        ),
        (
            "specialists_count",
            lambda card: card.specialists_count is None,
            "Quantos especialistas receberiam os atendimentos qualificados?",
        ),
    ]
    for key, predicate, text in candidates:
        if key in skip_fields:
            continue
        if predicate(contact_card):
            return QuestionPick(key=key, text=text)
    return None


def _combine_ack_and_question(ack: str, question: str) -> str:
    if not question:
        return ack
    return f"{ack} {question}"


def _format_tools(tools: list[str]) -> str:
    if not tools:
        return "ferramentas basicas"
    normalized = [tool.replace("_", " ") for tool in tools[:3]]
    return ", ".join(normalized)


_MESSAGE_VOLUME_KEYWORDS = (
    "mensagens por dia",
    "mensagens/dia",
    "volume de mensagens",
    "quantas mensagens",
    "qtd mensagens",
    "quantidade de mensagens",
    "atendimentos por dia",
    "volume diario",
)

_ATTENDANTS_KEYWORDS = (
    "quantas pessoas atendem",
    "quantas pessoas atendendo",
    "pessoas atendendo",
    "equipe de atendimento",
    "quantos atendentes",
    "time de atendimento",
)

_SPECIALISTS_KEYWORDS = (
    "quantos advogados",
    "quantos especialistas",
    "quantos profissionais",
    "quantos consultores",
)

_CRM_KEYWORDS = (
    "crm",
    "integra com crm",
    "integracao com crm",
    "ja usa crm",
    "ja tem crm",
    "usa crm",
    "tem crm",
)

_TOOLS_KEYWORDS = (
    "planilha",
    "whatsapp web",
    "ferramenta",
    "ferramentas",
    "como se organizam",
    "como organizam",
)
