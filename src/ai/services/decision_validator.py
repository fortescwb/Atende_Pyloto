"""DecisionValidator (3 gates) separado do OttoAgent."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai.models.otto import OttoDecision, OttoRequest
from ai.models.validation import ValidationResult
from ai.rules.otto_guardrails import (
    contains_disallowed_pii,
    contains_prohibited_promises,
    is_response_length_valid,
)
from ai.rules.otto_next_state import detect_has_new_question, normalize_next_state

if TYPE_CHECKING:
    from app.protocols.decision_review_client import DecisionReviewClientProtocol

logger = logging.getLogger(__name__)

_MAX_RESPONSE_CHARS = 500
# Confidence aqui indica intenção comercial (não confiabilidade).
# Não deve bloquear resposta; use apenas para acionar revisão opcional.
_CONFIDENCE_APPROVE = 0.85
_HANDOFF_TEXT = (
    "Vou conectar voce com nossa equipe para continuar o atendimento. "
    "Aguarde um momento."
)


class DecisionValidatorService:
    """Aplica gates determinístico, thresholds e revisão opcional."""

    def __init__(self, review_client: DecisionReviewClientProtocol | None = None) -> None:
        self._review_client = review_client

    async def validate(
        self,
        decision: OttoDecision,
        request: OttoRequest,
    ) -> tuple[OttoDecision, ValidationResult]:
        decision = _apply_next_state_normalization(decision, request)
        gate1 = self._gate_deterministic(decision, request)
        if gate1 is not None:
            return gate1

        gate2 = await self._gate_confidence(decision, request)
        return gate2

    def _gate_deterministic(
        self,
        decision: OttoDecision,
        request: OttoRequest,
    ) -> tuple[OttoDecision, ValidationResult] | None:
        if decision.requires_human:
            return decision, _result("human_required", reason="flag_requires_human")

        if not _is_transition_valid(decision.next_state, request):
            return _handoff("invalid_transition", correlation_id=request.correlation_id)

        if not is_response_length_valid(decision.response_text, max_chars=_MAX_RESPONSE_CHARS):
            return _handoff("invalid_response_size", correlation_id=request.correlation_id)

        if contains_disallowed_pii(decision.response_text):
            return _handoff("pii_detected", correlation_id=request.correlation_id)

        if contains_prohibited_promises(decision.response_text):
            return _handoff("prohibited_promise", correlation_id=request.correlation_id)

        return None

    async def _gate_confidence(
        self,
        decision: OttoDecision,
        request: OttoRequest,
    ) -> tuple[OttoDecision, ValidationResult]:
        if decision.confidence < _CONFIDENCE_APPROVE:
            if self._review_client is None:
                updated = decision.model_copy(update={"requires_human": True})
                updated = _apply_next_state_normalization(updated, request)
                return updated, _result("human_required", reason="mid_confidence_no_reviewer")

            reviewed = await self._review_client.review(decision=decision, request=request)
            if reviewed is None:
                return _handoff("review_failed", correlation_id=request.correlation_id)

            if reviewed.requires_human:
                return _handoff("review_requires_human", correlation_id=request.correlation_id)

            return reviewed, _result("approved", reviewer_used=True)

        return decision, _result("approved")


def _handoff(reason: str, *, correlation_id: str | None) -> tuple[OttoDecision, ValidationResult]:
    logger.info(
        "decision_validator_handoff",
        extra={
            "component": "decision_validator",
            "action": "handoff",
            "result": "human_required",
            "reason": reason,
            "correlation_id": correlation_id,
        },
    )
    decision = OttoDecision(
        next_state="HANDOFF_HUMAN",
        response_text=_HANDOFF_TEXT,
        message_type="text",
        confidence=0.0,
        requires_human=True,
        reasoning_debug=reason,
    )
    return decision, _result("human_required", reason=reason, corrections=decision.model_dump())


def _result(
    validation_type: str,
    *,
    reason: str | None = None,
    corrections: dict | None = None,
    reviewer_used: bool = False,
) -> ValidationResult:
    return ValidationResult(
        approved=validation_type == "approved",
        validation_type=validation_type,  # type: ignore[arg-type]
        corrections=corrections or {},
        escalation_reason=reason,
        reviewer_used=reviewer_used,
    )


def _is_transition_valid(next_state: str, request: OttoRequest) -> bool:
    valid_transitions = list(request.valid_transitions)
    if not valid_transitions:
        return next_state == request.session_state
    return next_state in valid_transitions


def _apply_next_state_normalization(decision: OttoDecision, request: OttoRequest) -> OttoDecision:
    has_question = detect_has_new_question(decision.response_text or "")
    normalized = normalize_next_state(
        proposed_state=decision.next_state,
        valid_transitions=request.valid_transitions,
        has_new_question=has_question,
        requires_human=decision.requires_human,
    )
    if normalized == decision.next_state:
        return decision
    logger.info(
        "otto_next_state_normalized",
        extra={
            "component": "decision_validator",
            "action": "normalize_next_state",
            "result": "updated",
            "correlation_id": request.correlation_id,
            "from_state": decision.next_state,
            "to_state": normalized,
            "has_question": has_question,
            "requires_human": decision.requires_human,
        },
    )
    return decision.model_copy(update={"next_state": normalized})
