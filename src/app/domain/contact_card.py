"""ContactCard - perfil do lead/contato persistido no Firestore.

Modelo focado em dados de qualificacao e contexto para o atendimento.
Evita PII em logs; PII fica apenas no modelo persistido.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

_PHONE_REGEX = re.compile(r"^\d{12,15}$")


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ContactCard(BaseModel):
    """Perfil do lead armazenado no Firestore."""

    # Identificacao (sempre disponivel no webhook)
    wa_id: str = Field(..., description="WhatsApp ID unico", pattern=r"^\d{12,15}$")
    phone: str = Field(..., description="Telefone internacional", pattern=r"^\d{12,15}$")
    whatsapp_name: str = Field(..., description="Nome salvo no WhatsApp")

    # Dados pessoais (extraidos)
    full_name: str | None = None
    email: str | None = Field(None, pattern=r"^[^@]+@[^@]+\.[^@]+$")
    company: str | None = None
    role: str | None = None
    location: str | None = None

    # Interesse e qualificacao
    primary_interest: Literal[
        "saas", "sob_medida", "gestao_perfis_trafego",
        "automacao_atendimento", "intermediacao_entregas",
        "gestao_perfis", "trafego_pago", "intermediacao",
    ] | None = None
    secondary_interests: list[str] = Field(default_factory=list)
    urgency: Literal["low", "medium", "high", "urgent"] | None = None
    budget_indication: str | None = Field(None, max_length=100)
    specific_need: str | None = Field(None, max_length=200)
    company_size: Literal["mei", "micro", "pequena", "media", "grande"] | None = None

    # Scores
    qualification_score: float = Field(default=0.0, ge=0.0, le=100.0)
    is_qualified: bool = False

    # Metadados
    first_contact_at: datetime = Field(default_factory=_utcnow)
    last_updated_at: datetime = Field(default_factory=_utcnow)
    last_message_at: datetime | None = None
    total_messages: int = Field(default=0, ge=0)

    # Flags
    requested_human: bool = False
    showed_objection: bool = False
    was_notified_to_team: bool = False

    # Metadata adicional
    custom_metadata: dict[str, Any] = Field(default_factory=dict)

    def calculate_qualification_score(self) -> float:
        """Calcula score de qualificacao baseado em campos preenchidos."""
        score = 0.0
        if self.full_name:
            score += 15
        if self.email:
            score += 15
        if self.company:
            score += 10
        if self.primary_interest:
            score += 20
        if self.specific_need:
            score += 15
        if self.urgency in ("high", "urgent"):
            score += 15
        if self.budget_indication:
            score += 10

        self.qualification_score = score
        self.is_qualified = score >= 60
        self.last_updated_at = _utcnow()
        return score

    def to_prompt_summary(self) -> str:
        """Resumo curto para prompt (max ~200 tokens)."""
        parts: list[str] = []
        parts.append(f"WhatsApp: {self.whatsapp_name} ({self.phone})")

        if self.full_name and self.full_name.lower() != self.whatsapp_name.lower():
            parts.append(f"Nome completo: {self.full_name}")

        if self.company:
            size_str = f" ({self.company_size})" if self.company_size else ""
            parts.append(f"Empresa: {self.company}{size_str}")

        if self.role:
            parts.append(f"Cargo: {self.role}")

        if self.email:
            parts.append(f"Email: {self.email}")

        if self.primary_interest:
            interest_display = self.primary_interest.replace("_", " ").title()
            parts.append(f"Interesse principal: {interest_display}")
            if self.secondary_interests:
                secondary = ", ".join(
                    i.replace("_", " ").title() for i in self.secondary_interests
                )
                parts.append(f"Outros interesses: {secondary}")
        else:
            parts.append("Interesse: ainda nao identificado")

        if self.specific_need:
            parts.append(f"Necessidade: {self.specific_need}")

        if self.urgency:
            urgency_map = {
                "low": "Baixa",
                "medium": "Media",
                "high": "Alta",
                "urgent": "Urgente",
            }
            parts.append(f"Urgencia: {urgency_map[self.urgency]}")

        if self.budget_indication:
            parts.append(f"Orcamento: {self.budget_indication}")

        status = "QUALIFICADO" if self.is_qualified else "Qualificando"
        parts.append(f"Score: {self.qualification_score:.0f}/100 {status}")

        alerts: list[str] = []
        if self.requested_human:
            alerts.append("Solicitou atendimento humano")
        if self.showed_objection:
            alerts.append("Levantou objecao")
        if self.is_qualified and not self.was_notified_to_team:
            alerts.append("Lead qualificado nao notificado")
        if alerts:
            parts.append(f"Atencao: {' | '.join(alerts)}")

        return "\n".join(parts)

    def to_firestore_dict(self) -> dict[str, Any]:
        """Converte para dict compativel com Firestore (sem None)."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_firestore_dict(cls, data: dict[str, Any]) -> ContactCard:
        """Cria instancia a partir de documento Firestore."""
        for key in ("first_contact_at", "last_updated_at", "last_message_at"):
            value = data.get(key)
            if isinstance(value, str):
                data[key] = datetime.fromisoformat(value)
        return cls(**data)

    @field_validator("wa_id", "phone")
    @classmethod
    def validate_phone_format(cls, value: str) -> str:
        """Valida formato internacional do telefone."""
        if not _PHONE_REGEX.match(value):
            raise ValueError("Telefone deve ter 12-15 digitos")
        return value


class ContactCardPatch(BaseModel):
    """Patch parcial do ContactCard (apenas campos atualizados)."""

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
