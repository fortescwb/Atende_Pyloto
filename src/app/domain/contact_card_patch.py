"""Patch parcial do ContactCard (apenas campos atualizados)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ContactCardPatch(BaseModel):
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
    message_volume_per_day: int | None = Field(None, ge=0)
    attendants_count: int | None = Field(None, ge=0)
    specialists_count: int | None = Field(None, ge=0)
    has_crm: bool | None = None
    current_tools: list[str] | None = None
    requested_human: bool | None = None
    showed_objection: bool | None = None

    def has_updates(self) -> bool:
        return any(value is not None for value in self.model_dump().values())

