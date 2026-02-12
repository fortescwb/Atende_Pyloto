"""Guards deterministicos para melhorar continuidade do Otto.

- Evita repeticao/irrelevancia de perguntas via ContactCard.
- Injeta continuidade quando o Otto "trava".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.services.otto_guard_detection import detect_question_type, is_confirmation_message
from app.services.otto_guard_funnel_copy import build_ack
from app.services.otto_guard_funnel_questions import build_next_step_cta, pick_next_question
from app.services.otto_guard_funnel_state import (
    has_minimum_qualification,
    is_already_known,
    is_relevant_question,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ai.models.otto import OttoDecision
    from app.domain.contact_card import ContactCard


@dataclass(frozen=True, slots=True)
class GuardResult:
    decision: OttoDecision
    applied: bool
    question_type: str | None = None
    next_question_key: str | None = None
    guard_type: str | None = None


def apply_business_hours_guard(
    *,
    decision: OttoDecision,
    recent_fields: Iterable[str] | None = None,
) -> GuardResult:
    """Bloqueia horarios fora do expediente (09h-17h).

    O sinal e passado via `recent_fields` para manter o guard deterministico
    (sem parse complexo aqui).
    """
    recent = set(recent_fields or [])
    if "meeting_time_out_of_hours" not in recent:
        return GuardResult(decision=decision, applied=False)

    replacement = (
        "Nosso horario de atendimento e de 9h as 17h (seg-sex). "
        "Qual dia e horario dentro desse periodo fica melhor pra voce?"
    )
    return GuardResult(
        decision=decision.model_copy(update={"response_text": replacement}),
        applied=True,
        guard_type="business_hours",
    )


async def _apply_repetition_guard_async(
    *,
    decision: OttoDecision,
    contact_card: ContactCard | None,
    recent_fields: Iterable[str] | None = None,
) -> GuardResult:
    """Async implementation of apply_repetition_guard."""
    if contact_card is None:
        return GuardResult(decision=decision, applied=False)

    response_text = (decision.response_text or "").strip()
    if not response_text:
        return GuardResult(decision=decision, applied=False)

    question_type = detect_question_type(response_text)
    if question_type is None:
        return GuardResult(decision=decision, applied=False)

    already_known = is_already_known(contact_card, question_type)
    relevant = is_relevant_question(contact_card, question_type)
    if not already_known and relevant:
        return GuardResult(decision=decision, applied=False)

    ack = build_ack(contact_card, question_type, recent_fields=recent_fields)
    next_pick = pick_next_question(contact_card, skip_fields={question_type})
    cta = await build_next_step_cta(contact_card)

    next_text = next_pick.text if next_pick else cta
    if not next_text:
        return GuardResult(decision=decision, applied=False)

    updated = decision.model_copy(update={"response_text": _combine(ack, next_text)})
    guard_type = "repetition" if already_known else "irrelevant_question"
    return GuardResult(
        decision=updated,
        applied=True,
        question_type=question_type,
        next_question_key=next_pick.key if next_pick else None,
        guard_type=guard_type,
    )


def apply_repetition_guard(
    *,
    decision: OttoDecision,
    contact_card: ContactCard | None,
    recent_fields: Iterable[str] | None = None,
):
    """Compatibility wrapper: returns GuardResult synchronously when called from sync code,
    or returns coroutine when called from async context (caller should await)."""
    coro = _apply_repetition_guard_async(
        decision=decision, contact_card=contact_card, recent_fields=recent_fields
    )
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return coro
    except RuntimeError:
        # No running loop
        pass
    return asyncio.run(coro)


async def _apply_continuation_guard_async(
    *,
    decision: OttoDecision,
    contact_card: ContactCard | None,
    user_message: str,
    recent_fields: Iterable[str] | None = None,
) -> GuardResult:
    """Async implementation of apply_continuation_guard."""
    if contact_card is None:
        return GuardResult(decision=decision, applied=False)

    text = (decision.response_text or "").strip()
    if not text:
        return GuardResult(decision=decision, applied=False)
    if "?" in text:
        return GuardResult(decision=decision, applied=False)

    trigger = is_confirmation_message(user_message) or bool(list(recent_fields or []))
    if not trigger:
        return GuardResult(decision=decision, applied=False)

    next_pick = pick_next_question(contact_card, skip_fields=set())
    cta = await build_next_step_cta(contact_card)

    next_text = ""
    if has_minimum_qualification(contact_card) and cta:
        next_text = cta
    elif next_pick:
        next_text = next_pick.text
    elif cta:
        next_text = cta

    if not next_text:
        return GuardResult(decision=decision, applied=False)

    updated = decision.model_copy(update={"response_text": _combine(text, next_text)})
    return GuardResult(
        decision=updated,
        applied=True,
        next_question_key=next_pick.key if next_pick else None,
        guard_type="continuation",
    )


def apply_continuation_guard(
    *,
    decision: OttoDecision,
    contact_card: ContactCard | None,
    user_message: str,
    recent_fields: Iterable[str] | None = None,
):
    """Compatibility wrapper: returns GuardResult synchronously when called from sync code,
    or returns coroutine when called from async context (caller should await)."""
    coro = _apply_continuation_guard_async(
        decision=decision,
        contact_card=contact_card,
        user_message=user_message,
        recent_fields=recent_fields,
    )
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return coro
    except RuntimeError:
        # No running loop
        pass
    return asyncio.run(coro)


def collect_contact_card_fields(contact_card: ContactCard | None) -> list[str]:
    """Retorna lista de campos nao sensiveis presentes no ContactCard (apenas chaves)."""
    if contact_card is None:
        return []

    fields: list[str] = []
    for key in (
        "primary_interest",
        "secondary_interests",
        "specific_need",
        "urgency",
        "budget_indication",
        "company_size",
        "message_volume_per_day",
        "attendants_count",
        "specialists_count",
        "has_crm",
        "current_tools",
        "users_count",
        "modules_needed",
        "desired_features",
        "integrations_needed",
        "needs_data_migration",
        "meeting_preferred_datetime_text",
        "meeting_mode",
    ):
        value = getattr(contact_card, key, None)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, list) and not value:
            continue
        fields.append(key)

    if contact_card.full_name:
        fields.append("full_name")
    if contact_card.email:
        fields.append("email")
    if contact_card.company:
        fields.append("company")
    if contact_card.requested_human:
        fields.append("requested_human")
    if contact_card.showed_objection:
        fields.append("showed_objection")

    return fields


def _combine(first: str, second: str) -> str:
    if not second:
        return first
    return f"{first} {second}"
