"""Modelos de validação de decisão (DecisionValidator)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """Resultado da validação em múltiplos gates."""

    approved: bool = Field(default=False, description="True se decisão pode seguir sem bloqueio")
    validation_type: Literal["approved", "auto_corrected", "human_required", "review_pending"]
    corrections: dict[str, Any] = Field(default_factory=dict)
    escalation_reason: str | None = None
    reviewer_used: bool = False

    @property
    def requires_human(self) -> bool:
        """Convenience flag."""
        return self.validation_type == "human_required"
