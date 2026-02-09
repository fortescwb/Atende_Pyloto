"""Extrator de payloads WhatsApp Business API.

Responsabilidades:
- Extrair mensagens do payload bruto do webhook
- Converter para estrutura intermediária padronizada
- Suportar todos os tipos de mensagem (text, media, location, etc.)

Não faz validação de negócio - apenas extração estrutural.
"""

from __future__ import annotations

import logging
from typing import Any

from ._extraction_helpers import (
    extract_address_message,
    extract_contacts_message,
    extract_interactive_message,
    extract_location_message,
    extract_media_message,
    extract_reaction_message,
    extract_text_message,
)

logger = logging.getLogger(__name__)

SUPPORTED_MESSAGE_TYPES = frozenset(
    {
        "text", "image", "video", "audio",
        "document", "sticker", "location", "address",
        "contacts", "interactive", "reaction", "button",
        "order", "system", "request_welcome", "ephemeral",
    }
)

_FIELD_NAMES = (
    "text", "media_id", "media_url", "media_filename", "media_mime_type",
    "location_latitude", "location_longitude", "location_name", "location_address",
    "address_street", "address_city", "address_state", "address_zip_code", "address_country_code",
    "contacts_json", "interactive_type", "interactive_button_id", "interactive_list_id",
    "interactive_cta_url", "flow_response_json", "reaction_message_id", "reaction_emoji",
)


def _create_empty_fields() -> dict[str, Any]:
    """Cria dicionário com todos os campos zerados."""
    return dict.fromkeys(_FIELD_NAMES, None)

def _extract_fields_by_type(
    msg: dict[str, Any],
    message_type: str | None,
    fields: dict[str, Any],
) -> None:
    """Extrai campos do payload de acordo com o tipo de mensagem."""
    if _extract_simple_type(msg, message_type, fields):
        return
    if message_type == "interactive":
        _extract_interactive_fields(msg, fields)
        return
    if message_type and message_type not in SUPPORTED_MESSAGE_TYPES:
        logger.info("unsupported_message_type_received", extra={"message_type": message_type})


def _extract_simple_type(
    msg: dict[str, Any],
    message_type: str | None,
    fields: dict[str, Any],
) -> bool:
    if message_type == "text":
        fields["text"], _ = extract_text_message(msg)
        return True
    if message_type in ("image", "video", "audio", "document", "sticker"):
        (
            fields["media_id"],
            fields["media_url"],
            fields["media_filename"],
            fields["media_mime_type"],
        ) = extract_media_message(msg, message_type)
        return True
    if message_type == "location":
        (
            fields["location_latitude"],
            fields["location_longitude"],
            fields["location_name"],
            fields["location_address"],
        ) = extract_location_message(msg)
        return True
    if message_type == "address":
        (
            fields["address_street"],
            fields["address_city"],
            fields["address_state"],
            fields["address_zip_code"],
            fields["address_country_code"],
        ) = extract_address_message(msg)
        return True
    if message_type == "contacts":
        fields["contacts_json"] = extract_contacts_message(msg)
        return True
    if message_type == "reaction":
        fields["reaction_message_id"], fields["reaction_emoji"] = extract_reaction_message(msg)
        return True
    return False


def _extract_interactive_fields(msg: dict[str, Any], fields: dict[str, Any]) -> None:
    (
        fields["interactive_type"],
        fields["interactive_button_id"],
        fields["interactive_list_id"],
        fields["flow_response_json"],
    ) = extract_interactive_message(msg)
    interactive_block = msg.get("interactive") or {}
    if not isinstance(interactive_block, dict):
        return
    cta_block = interactive_block.get("cta_url_reply") or {}
    if isinstance(cta_block, dict):
        fields["interactive_cta_url"] = cta_block.get("url")


def extract_payload_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai mensagens do payload bruto para estrutura intermediária."""
    messages: list[dict[str, Any]] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = value.get("contacts") or []
            whatsapp_name = None
            if contacts and isinstance(contacts[0], dict):
                profile = contacts[0].get("profile") or {}
                if isinstance(profile, dict):
                    whatsapp_name = profile.get("name")
            for msg in value.get("messages", []) or []:
                message_id = msg.get("id")
                if not message_id:
                    continue
                message_type = msg.get("type")
                fields = _create_empty_fields()
                _extract_fields_by_type(msg, message_type, fields)
                messages.append(
                    {
                        "message_id": message_id,
                        "from_number": msg.get("from"),
                        "timestamp": msg.get("timestamp"),
                        "message_type": message_type or "unknown",
                        "whatsapp_name": whatsapp_name,
                        "fields": fields,
                    }
                )
    return messages
