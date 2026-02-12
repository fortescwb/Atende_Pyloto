"""Contrato de calendario para uso no dominio de agendamentos.

Mantemos apenas o protocolo aqui para permitir troca de provider sem
impactar os casos de uso que dependem da capacidade de agenda.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.domain.appointment import AppointmentData, CalendarEvent, TimeSlot


@runtime_checkable
class CalendarServiceProtocol(Protocol):
    """Contrato para operacoes de disponibilidade e eventos de calendario."""

    async def check_availability(
        self,
        date: str,
        *,
        start_hour: int = 9,
        end_hour: int = 17,
    ) -> list[TimeSlot]:
        """Retorna slots de disponibilidade para uma data especifica."""
        ...

    async def create_event(self, appointment: AppointmentData) -> CalendarEvent:
        """Cria evento no calendario com base nos dados de agendamento."""
        ...

    async def cancel_event(self, event_id: str) -> bool:
        """Cancela um evento existente e retorna sucesso da operacao."""
        ...

    async def get_event(self, event_id: str) -> CalendarEvent | None:
        """Busca um evento pelo identificador e retorna None se nao existir."""
        ...
