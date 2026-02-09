"""Implementações concretas de IO para IA.

Conforme REGRAS_E_PADROES.md § 2.3 — app/infra: implementações de IO.
Conforme REGRAS_E_PADROES.md § 2.1 — ai/ não faz IO direto.
"""

from app.infra.ai.decision_review_client import DecisionReviewClient
from app.infra.ai.otto_client import OttoClient

__all__ = [
    "DecisionReviewClient",
    "OttoClient",
]
