"""Reexports de modelos de protocolo para api/connectors.

Os contratos canônicos residem em app/protocols/models.py.
Este módulo expõe os tipos para consumidores na camada api/.
"""

from __future__ import annotations

from app.protocols.models import (
    InboundMessageEvent,
    NormalizedMessage,
    OutboundMessageRequest,
    OutboundMessageResponse,
    WebhookProcessingSummary,
)

# Alias por clareza semântica no contexto WhatsApp
NormalizedWhatsAppMessage = NormalizedMessage

__all__ = [
    "InboundMessageEvent",
    "NormalizedMessage",
    "NormalizedWhatsAppMessage",
    "OutboundMessageRequest",
    "OutboundMessageResponse",
    "WebhookProcessingSummary",
]
