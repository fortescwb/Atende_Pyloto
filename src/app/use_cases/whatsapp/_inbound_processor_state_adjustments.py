"""Ajustes determinísticos de estado para o fluxo inbound."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai.models.otto import OttoDecision

logger = logging.getLogger(__name__)


def adjust_for_meeting_question(
    *,
    decision: OttoDecision,
    valid: set[str],
    text: str,
    correlation_id: str,
    message_id: str | None,
) -> OttoDecision | None:
    asks_meeting_time = (
        ("agendar" in text and "?" in text)
        or "qual melhor dia" in text
        or "dia e horario" in text
        or "dia/hor" in text
    )
    if not (
        asks_meeting_time
        and "COLLECTING_INFO" in valid
        and decision.next_state != "COLLECTING_INFO"
    ):
        return None
    logger.info(
        "otto_next_state_adjusted",
        extra={
            "component": "otto_guard",
            "action": "adjust_next_state",
            "result": "updated",
            "correlation_id": correlation_id,
            "message_id": message_id,
            "from_state": decision.next_state,
            "to_state": "COLLECTING_INFO",
            "reason": "asking_meeting_time",
        },
    )
    return decision.model_copy(update={"next_state": "COLLECTING_INFO"})


def adjust_for_meeting_collected(
    *,
    decision: OttoDecision,
    valid: set[str],
    text: str,
    contact_card: Any,
    correlation_id: str,
    message_id: str | None,
) -> OttoDecision | None:
    meeting_text = getattr(contact_card, "meeting_preferred_datetime_text", None)
    email = getattr(contact_card, "email", None)
    should_close = bool(meeting_text) and bool(email) and "?" not in text
    if not should_close:
        return None
    if "SCHEDULED_FOLLOWUP" not in valid or decision.next_state == "SCHEDULED_FOLLOWUP":
        return None
    logger.info(
        "otto_next_state_adjusted",
        extra={
            "component": "otto_guard",
            "action": "adjust_next_state",
            "result": "updated",
            "correlation_id": correlation_id,
            "message_id": message_id,
            "from_state": decision.next_state,
            "to_state": "SCHEDULED_FOLLOWUP",
            "reason": "meeting_collected",
        },
    )
    debug = decision.reasoning_debug or ""
    updated_debug = f"{debug} | scheduling_triggered=true".strip(" |")
    return decision.model_copy(
        update={
            "next_state": "SCHEDULED_FOLLOWUP",
            "reasoning_debug": updated_debug,
        }
    )
