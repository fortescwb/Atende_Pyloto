"""Enums de domínio para tipos de mensagem WhatsApp."""

from __future__ import annotations

from enum import StrEnum


class MessageType(StrEnum):
    """Tipos de conteúdo suportados pela API Meta/WhatsApp."""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACTS = "contacts"
    ADDRESS = "address"
    INTERACTIVE = "interactive"
    TEMPLATE = "template"
    REACTION = "reaction"


class InteractiveType(StrEnum):
    """Tipos de mensagens interativas suportadas."""

    BUTTON = "button"
    LIST = "list"
    FLOW = "flow"
    CTA_URL = "cta_url"
    LOCATION_REQUEST_MESSAGE = "location_request_message"


class MessageCategory(StrEnum):
    """Categorias de mensagens conforme política Meta/WhatsApp."""

    MARKETING = "MARKETING"
    UTILITY = "UTILITY"
    AUTHENTICATION = "AUTHENTICATION"
    SERVICE = "SERVICE"
