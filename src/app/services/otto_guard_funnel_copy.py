"""Mensagens curtas (copy) do funil para os guards.

Centraliza acknowledgements e helpers para manter os guards pequenos.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from app.domain.contact_card import ContactCard


def build_ack(
    contact_card: ContactCard,
    question_type: str,
    *,
    recent_fields: Iterable[str] | None,
) -> str:
    """Constroi um acknowledgement curto sem repetir sempre o mesmo fato."""
    recent = set(recent_fields or [])

    if "meeting_preferred_datetime_text" in recent and contact_card.meeting_preferred_datetime_text:
        return "Perfeito, obrigado."
    if "attendants_count" in recent and contact_card.attendants_count is not None:
        return f"Entendi, sao {contact_card.attendants_count} pessoas atendendo hoje."
    if "specialists_count" in recent and contact_card.specialists_count is not None:
        return f"Entendi, {contact_card.specialists_count} especialistas recebem os atendimentos."
    if "current_tools" in recent and contact_card.current_tools:
        tools = _format_tools(contact_card.current_tools)
        return f"Entendi, hoje voces usam {tools}."
    if "has_crm" in recent and contact_card.has_crm is not None:
        if contact_card.has_crm is False:
            return "Entendi, voce ainda nao usa CRM."
        return "Entendi, voce ja usa CRM."
    if "message_volume_per_day" in recent and contact_card.message_volume_per_day is not None:
        volume = contact_card.message_volume_per_day
        return f"Entendi, voce recebe cerca de {volume} msgs/dia."

    if (
        question_type == "message_volume_per_day"
        and contact_card.message_volume_per_day is not None
    ):
        volume = contact_card.message_volume_per_day
        return f"Entendi, voce recebe cerca de {volume} msgs/dia."
    if question_type == "attendants_count" and contact_card.attendants_count is not None:
        return f"Entendi, sao {contact_card.attendants_count} pessoas atendendo hoje."
    if question_type == "specialists_count" and contact_card.specialists_count is not None:
        return f"Entendi, {contact_card.specialists_count} especialistas recebem os atendimentos."
    if question_type == "has_crm":
        if contact_card.has_crm is True or "crm" in contact_card.current_tools:
            return "Entendi, voce ja usa CRM."
        return "Entendi, voce ainda nao usa CRM."
    if question_type == "current_tools" and contact_card.current_tools:
        tools = _format_tools(contact_card.current_tools)
        return f"Entendi, hoje voces usam {tools}."
    has_meeting = bool(contact_card.meeting_preferred_datetime_text)
    if question_type == "meeting_preferred_datetime_text" and has_meeting:
        return "Perfeito, obrigado."
    return "Entendi."


def _format_tools(tools: list[str]) -> str:
    if not tools:
        return "ferramentas basicas"
    normalized = [tool.replace("_", " ") for tool in tools[:3]]
    return ", ".join(normalized)
