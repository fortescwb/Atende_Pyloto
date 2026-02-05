"""Implementação simples do reviewer para Gate 3.

Atualmente retorna a própria decisão (pass-through) para manter determinismo
e permitir injeção futura de modelo barato com timeout curto.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.protocols.decision_review_client import DecisionReviewClientProtocol

if TYPE_CHECKING:
    from ai.models.otto import OttoDecision, OttoRequest
else:  # pragma: no cover
    OttoDecision = object
    OttoRequest = object


class DecisionReviewClient(DecisionReviewClientProtocol):
    """Reviewer leve (stub)."""

    async def review(self, *, decision: OttoDecision, request: OttoRequest) -> OttoDecision | None:
        return decision
