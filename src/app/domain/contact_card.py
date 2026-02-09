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
    message_volume_per_day: int | None = Field(None, ge=0)
    attendants_count: int | None = Field(None, ge=0)
    specialists_count: int | None = Field(None, ge=0)
    has_crm: bool | None = None
    current_tools: list[str] = Field(default_factory=list)
    users_count: int | None = Field(None, ge=0)
    modules_needed: list[str] = Field(default_factory=list)

    # Sob medida (qualificacao)
    desired_features: list[str] = Field(default_factory=list)
    integrations_needed: list[str] = Field(default_factory=list)
    legacy_systems: list[str] = Field(default_factory=list)
    needs_data_migration: bool | None = None

    # Agendamento (handoff)
    meeting_preferred_datetime_text: str | None = Field(None, max_length=120)
    meeting_mode: Literal["online", "presencial"] | None = None

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
        parts.append(f"WhatsApp: {self.whatsapp_name}")
        _append_profile_lines(self, parts)
        _append_interest_lines(self, parts)
        _append_status_lines(self, parts)
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


def _append_profile_lines(card: ContactCard, parts: list[str]) -> None:
    if card.full_name and card.full_name.lower() != card.whatsapp_name.lower():
        parts.append(f"Nome completo: {card.full_name}")
    if card.company:
        size_str = f" ({card.company_size})" if card.company_size else ""
        parts.append(f"Empresa: {card.company}{size_str}")
    _append_if_present(parts, "Cargo", card.role)
    _append_if_not_none(parts, "Volume/dia", card.message_volume_per_day)
    _append_if_not_none(parts, "Equipe atendimento", card.attendants_count)
    _append_if_not_none(parts, "Especialistas", card.specialists_count)
    if card.has_crm is not None:
        parts.append(f"CRM: {'Sim' if card.has_crm else 'Nao'}")
    if card.current_tools:
        parts.append(f"Ferramentas atuais: {', '.join(card.current_tools)}")
    _append_if_not_none(parts, "Usuarios", card.users_count)
    _append_limited_list(parts, "Modulos", card.modules_needed, 6)
    _append_limited_list(parts, "Funcionalidades", card.desired_features, 6)
    _append_limited_list(parts, "Integracoes", card.integrations_needed, 6)
    if card.needs_data_migration is not None:
        parts.append(f"Migracao de dados: {'Sim' if card.needs_data_migration else 'Nao'}")
    _append_limited_list(parts, "Legado", card.legacy_systems, 4)
    _append_if_present(parts, "Email", card.email)


def _append_interest_lines(card: ContactCard, parts: list[str]) -> None:
    if card.primary_interest:
        interest_display = card.primary_interest.replace("_", " ").title()
        parts.append(f"Interesse principal: {interest_display}")
        if card.secondary_interests:
            secondary = ", ".join(i.replace("_", " ").title() for i in card.secondary_interests)
            parts.append(f"Outros interesses: {secondary}")
    else:
        parts.append("Interesse: ainda nao identificado")
    _append_if_present(parts, "Necessidade", card.specific_need)
    if card.urgency:
        parts.append(f"Urgencia: {_urgency_label(card.urgency)}")
    _append_if_present(parts, "Orcamento", card.budget_indication)
    if card.meeting_preferred_datetime_text:
        mode = f" ({card.meeting_mode})" if card.meeting_mode else ""
        parts.append(f"Agendamento: {card.meeting_preferred_datetime_text}{mode}")


def _append_status_lines(card: ContactCard, parts: list[str]) -> None:
    status = "QUALIFICADO" if card.is_qualified else "Qualificando"
    parts.append(f"Score: {card.qualification_score:.0f}/100 {status}")
    alerts: list[str] = []
    if card.requested_human:
        alerts.append("Solicitou atendimento humano")
    if card.showed_objection:
        alerts.append("Levantou objecao")
    if card.is_qualified and not card.was_notified_to_team:
        alerts.append("Lead qualificado nao notificado")
    if alerts:
        parts.append(f"Atencao: {' | '.join(alerts)}")


def _append_if_not_none(parts: list[str], label: str, value: int | None) -> None:
    if value is not None:
        parts.append(f"{label}: {value}")


def _append_if_present(parts: list[str], label: str, value: str | None) -> None:
    if value:
        parts.append(f"{label}: {value}")


def _append_limited_list(parts: list[str], label: str, items: list[str], limit: int) -> None:
    if items:
        parts.append(f"{label}: {', '.join(items[:limit])}")


def _urgency_label(value: Literal["low", "medium", "high", "urgent"]) -> str:
    return {"low": "Baixa", "medium": "Media", "high": "Alta", "urgent": "Urgente"}[value]
