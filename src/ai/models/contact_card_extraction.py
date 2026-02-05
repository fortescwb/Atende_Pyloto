"""Models para ContactCardExtractor (Agente utilitario).

Define contratos de entrada/saida para extração de dados do ContactCard.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContactCardExtractionRequest(BaseModel):
    """Request para extração de dados do contato."""

    model_config = ConfigDict(extra="ignore")

    user_message: str
    contact_card_summary: str = ""
    conversation_context: list[str] | None = None


class ContactCardPatch(BaseModel):
    """Patch parcial do ContactCard (apenas campos atualizados)."""

    model_config = ConfigDict(extra="ignore")

    full_name: str | None = None
    email: str | None = None
    company: str | None = None
    role: str | None = None
    location: str | None = None
    primary_interest: Literal[
        "saas", "sob_medida", "gestao_perfis_trafego",
        "automacao_atendimento", "intermediacao_entregas",
        "gestao_perfis", "trafego_pago", "intermediacao",
    ] | None = None
    secondary_interests: list[str] | None = None
    urgency: Literal["low", "medium", "high", "urgent"] | None = None
    budget_indication: str | None = None
    specific_need: str | None = None
    company_size: Literal["mei", "micro", "pequena", "media", "grande"] | None = None
    requested_human: bool | None = None
    showed_objection: bool | None = None

    def has_updates(self) -> bool:
        """Retorna True se existir ao menos um campo preenchido."""
        return any(value is not None for value in self.model_dump().values())


class ContactCardExtractionResult(BaseModel):
    """Resultado da extração do ContactCard."""

    model_config = ConfigDict(extra="ignore")

    updates: ContactCardPatch = Field(default_factory=ContactCardPatch)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[str] | None = None
    error: str | None = None

    @property
    def has_updates(self) -> bool:
        """Retorna True se existir patch com atualizações."""
        return self.updates.has_updates()

    @classmethod
    def empty(cls) -> ContactCardExtractionResult:
        """Retorna resultado vazio (sem updates)."""
        return cls(updates=ContactCardPatch(), confidence=0.0)
