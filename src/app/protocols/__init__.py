"""Protocolos e contratos do core da aplicação."""

from .calendar_service import CalendarServiceProtocol
from .conversation_store import (
    ConversationMessage,
    ConversationStoreError,
    ConversationStoreProtocol,
    LeadData,
)
from .decision_audit_store import DecisionAuditStoreProtocol
from .decision_review_client import DecisionReviewClientProtocol
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
from .transcription_service import TranscriptionResult, TranscriptionServiceProtocol
from .validator import OutboundRequestValidatorProtocol, ValidationError

__all__ = [
    "AsyncDedupeProtocol",
    "AsyncSessionStoreProtocol",
    "CalendarServiceProtocol",
    "ConversationMessage",
    "ConversationStoreError",
    "ConversationStoreProtocol",
    "DecisionAuditStoreProtocol",
    "DecisionReviewClientProtocol",
    "DedupeProtocol",
    "InboundMessageEvent",
    "LeadData",
    "MessageNormalizerProtocol",
    "NormalizedMessage",
    "OutboundMessageRequest",
    "OutboundMessageResponse",
    "OutboundRequestValidatorProtocol",
    "OutboundSenderProtocol",
    "PayloadBuilderProtocol",
    "SessionStoreProtocol",
    "TranscriptionResult",
    "TranscriptionServiceProtocol",
    "ValidationError",
    "WebhookProcessingSummary",
    "WhatsAppHttpClientProtocol",
]
