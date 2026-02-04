"""Helpers de extração de campos por tipo de mensagem WhatsApp.

Separado de extractor.py para manter SRP e limite de 200 linhas.
Cada função extrai campos específicos de um tipo de mensagem.
"""

from __future__ import annotations

import json
from typing import Any


def extract_text_message(msg: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extrai corpo de mensagem de texto."""
    text_block = msg.get("text")
    if isinstance(text_block, dict):
        return text_block.get("body"), None
    return None, None


def extract_media_message(
    msg: dict[str, Any], media_type: str
) -> tuple[str | None, str | None, str | None, str | None]:
    """Extrai campos de mídia (image, video, audio, document, sticker)."""
    media_block = msg.get(media_type)
    if not isinstance(media_block, dict):
        return None, None, None, None
    return (
        media_block.get("id"),
        media_block.get("url"),
        media_block.get("filename"),
        media_block.get("mime_type"),
    )


def extract_location_message(
    msg: dict[str, Any],
) -> tuple[float | None, float | None, str | None, str | None]:
    """Extrai campos de localização."""
    location_block = msg.get("location")
    if not isinstance(location_block, dict):
        return None, None, None, None
    return (
        location_block.get("latitude"),
        location_block.get("longitude"),
        location_block.get("name"),
        location_block.get("address"),
    )


def extract_address_message(
    msg: dict[str, Any],
) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    """Extrai campos de endereço."""
    address_block = msg.get("address")
    if not isinstance(address_block, dict):
        return None, None, None, None, None
    return (
        address_block.get("street"),
        address_block.get("city"),
        address_block.get("state"),
        address_block.get("zip_code"),
        address_block.get("country_code"),
    )


def extract_contacts_message(msg: dict[str, Any]) -> str | None:
    """Extrai contatos como JSON serializado."""
    contacts_block = msg.get("contacts") or []
    if not isinstance(contacts_block, list) or not contacts_block:
        return None
    try:
        return json.dumps(contacts_block, ensure_ascii=False)
    except (TypeError, ValueError):
        return None


def extract_interactive_message(
    msg: dict[str, Any],
) -> tuple[str | None, str | None, str | None]:
    """Extrai campos de mensagem interativa."""
    interactive_block = msg.get("interactive")
    if not isinstance(interactive_block, dict):
        return None, None, None
    interactive_type = interactive_block.get("type")
    button_reply = interactive_block.get("button_reply") or {}
    if isinstance(button_reply, dict):
        button_id = button_reply.get("id")
        if button_id:
            return interactive_type, button_id, None
    list_reply = interactive_block.get("list_reply") or {}
    if isinstance(list_reply, dict):
        list_id = list_reply.get("id")
        if list_id:
            return interactive_type, None, list_id
    return interactive_type, None, None


def extract_reaction_message(msg: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extrai campos de reaction."""
    reaction_block = msg.get("reaction")
    if not isinstance(reaction_block, dict):
        return None, None
    return reaction_block.get("message_id"), reaction_block.get("emoji")
