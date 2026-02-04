"""Protocolos e contratos do core da aplicação."""

from .decision_audit_store import DecisionAuditStoreProtocol
from .dedupe import AsyncDedupeProtocol, DedupeProtocol
from .http_client import WhatsAppHttpClientProtocol
from .models import (
    InboundMessageEvent,
    NormalizedMessage,
    OutboundMessageRequest,
    OutboundMessageResponse,
    WebhookProcessingSummary,
)
from .normalizer import MessageNormalizerProtocol
from .outbound_sender import OutboundSenderProtocol
from .payload_builder import PayloadBuilderProtocol
from .session_store import AsyncSessionStoreProtocol, SessionStoreProtocol
from .validator import OutboundRequestValidatorProtocol, ValidationError

__all__ = [
    "AsyncDedupeProtocol",
    "AsyncSessionStoreProtocol",
    "DecisionAuditStoreProtocol",
    "DedupeProtocol",
    "InboundMessageEvent",
    "MessageNormalizerProtocol",
    "NormalizedMessage",
    "OutboundMessageRequest",
    "OutboundMessageResponse",
    "OutboundRequestValidatorProtocol",
    "OutboundSenderProtocol",
    "PayloadBuilderProtocol",
    "SessionStoreProtocol",
    "ValidationError",
    "WebhookProcessingSummary",
    "WhatsAppHttpClientProtocol",
]
