"""Modelos de dominio para agendamento com calendario.

Esses contratos ficam no dominio para compartilhar dados entre servicos
sem acoplar regras de negocio a detalhes de provider externo.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - usado em runtime pelo schema do Pydantic
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TimeSlot(BaseModel):
    """Representa um intervalo de horario para agendamento."""

    model_config = ConfigDict(extra="ignore")

    start: datetime = Field(..., description="Data/hora de inicio do slot.")
    end: datetime = Field(..., description="Data/hora de fim do slot.")
    available: bool = Field(..., description="Indica se o slot esta disponivel.")


class AppointmentData(BaseModel):
    """Dados necessarios para criar um agendamento no calendario."""

    model_config = ConfigDict(extra="ignore")

    date: str = Field(..., description="Data informada para o agendamento (YYYY-MM-DD).")
    time: str = Field(..., description="Horario informado para o agendamento (HH:MM).")
    duration_min: int = Field(
        default=30,
        ge=1,
        description="Duracao do encontro em minutos.",
    )
    attendee_name: str = Field(..., description="Nome da pessoa que vai participar.")
    attendee_email: str = Field(..., description="Email da pessoa convidada.")
    attendee_phone: str = Field(..., description="Telefone da pessoa convidada.")
    description: str = Field(
        default="",
        description="Descricao adicional do encontro.",
    )
    meeting_mode: Literal["online", "presencial"] = Field(
        ...,
        description="Formato do encontro.",
    )
    vertical: str = Field(
        default="",
        description="Vertical de negocio associada ao agendamento.",
    )


class CalendarEvent(BaseModel):
    """Representa um evento confirmado no provedor de calendario."""

    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(..., description="Identificador unico do evento no calendario.")
    html_link: str = Field(..., description="URL publica para visualizar o evento.")
    start: datetime = Field(..., description="Data/hora de inicio do evento.")
    end: datetime = Field(..., description="Data/hora de fim do evento.")
    status: str = Field(default="confirmed", description="Status atual do evento.")


__all__ = ["AppointmentData", "CalendarEvent", "TimeSlot"]
