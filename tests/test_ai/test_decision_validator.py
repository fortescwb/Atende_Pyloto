"""Testes para DecisionValidatorService."""

from __future__ import annotations

import pytest

from ai.models.otto import OttoDecision, OttoRequest
from ai.services.decision_validator import DecisionValidatorService


class ReviewClientOK:
    async def review(self, *, decision: OttoDecision, request: OttoRequest):
        return decision.model_copy(update={"confidence": 0.9})


class ReviewClientFail:
    async def review(self, *, decision: OttoDecision, request: OttoRequest):
        return None


def _req(valid_transitions: list[str] | None = None) -> OttoRequest:
    return OttoRequest(
        user_message="texto",
        session_state="TRIAGE",
        history=["Usuario: oi"],
        contact_card_summary="{}",
        valid_transitions=valid_transitions or ["COLLECTING_INFO"],
    )


@pytest.mark.asyncio
async def test_invalid_transition_triggers_handoff() -> None:
    validator = DecisionValidatorService()
    decision = OttoDecision(
        next_state="ERROR",
        response_text="ok",
        message_type="text",
        confidence=0.9,
        requires_human=False,
    )

    updated, result = await validator.validate(decision, _req())

    assert updated.next_state == "HANDOFF_HUMAN"
    assert result.requires_human is True
    assert result.escalation_reason == "invalid_transition"


@pytest.mark.asyncio
async def test_pii_triggers_handoff() -> None:
    validator = DecisionValidatorService()
    decision = OttoDecision(
        next_state="COLLECTING_INFO",
        response_text="Meu email é teste@example.com",
        message_type="text",
        confidence=0.9,
        requires_human=False,
    )

    updated, result = await validator.validate(decision, _req(["COLLECTING_INFO"]))

    assert updated.requires_human is True
    assert result.requires_human is True


@pytest.mark.asyncio
async def test_low_confidence_handoff() -> None:
    validator = DecisionValidatorService()
    decision = OttoDecision(
        next_state="COLLECTING_INFO",
        response_text="ok",
        message_type="text",
        confidence=0.5,
        requires_human=False,
    )

    updated, result = await validator.validate(decision, _req(["COLLECTING_INFO"]))

    assert updated.requires_human is True
    assert result.validation_type == "human_required"


@pytest.mark.asyncio
async def test_review_client_approves_gray_zone() -> None:
    validator = DecisionValidatorService(review_client=ReviewClientOK())
    decision = OttoDecision(
        next_state="COLLECTING_INFO",
        response_text="ok",
        message_type="text",
        confidence=0.8,
        requires_human=False,
    )

    updated, result = await validator.validate(decision, _req(["COLLECTING_INFO"]))

    assert updated.confidence == 0.9
    assert result.approved is True
    assert result.reviewer_used is True


@pytest.mark.asyncio
async def test_review_missing_fallback_human() -> None:
    validator = DecisionValidatorService(review_client=ReviewClientFail())
    decision = OttoDecision(
        next_state="COLLECTING_INFO",
        response_text="ok",
        message_type="text",
        confidence=0.8,
        requires_human=False,
    )

    updated, result = await validator.validate(decision, _req(["COLLECTING_INFO"]))

    assert updated.requires_human is True
    assert result.validation_type == "human_required"
