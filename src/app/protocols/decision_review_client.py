"""Protocolo para reviewer LLM (Gate 3 do DecisionValidator)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ai.models.otto import OttoDecision, OttoRequest
else:  # pragma: no cover - usado apenas para type checking
    OttoDecision = object
    OttoRequest = object


class DecisionReviewClientProtocol(Protocol):
    """Cliente de revisão de decisão via LLM barato."""

    async def review(self, *, decision: OttoDecision, request: OttoRequest) -> OttoDecision | None:
        """Recebe decisão inicial e retorna decisão revisada ou None em falha."""
