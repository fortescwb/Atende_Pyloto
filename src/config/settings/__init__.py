"""Agregador de settings do Atende_Pyloto.

Re-exporta todas as settings e funções de cada módulo.
Organização por domínio para isolamento de mudanças.
"""

from __future__ import annotations

# AI/LLM settings
from config.settings.ai import (
    FloodDetectionSettings,
    OpenAISettings,
    get_flood_detection_settings,
    get_openai_settings,
)

# Base settings
from config.settings.base import (
    BaseSettings,
    DedupeBackend,
    DedupeSettings,
    Environment,
    SessionSettings,
    SessionStoreBackend,
    get_base_settings,
    get_dedupe_settings,
    get_session_settings,
)

# Calendar settings
from config.settings.calendar import (
    CalendarSettings,
    get_calendar_settings,
)

# Infrastructure settings
from config.settings.infra import (
    CloudTasksSettings,
    FirestoreSettings,
    GCSSettings,
    InboundLogSettings,
    LogBackend,
    PubSubSettings,
    QueueBackend,
    get_cloud_tasks_settings,
    get_firestore_settings,
    get_gcs_settings,
    get_inbound_log_settings,
    get_pubsub_settings,
)

# Channel-specific settings
from config.settings.whatsapp import (
    GRAPH_API_BASE_URL,
    GRAPH_API_VERSION,
    WhatsAppSettings,
    get_whatsapp_settings,
)

__all__ = [
    # Constants
    "GRAPH_API_BASE_URL",
    "GRAPH_API_VERSION",
    # Base
    "BaseSettings",
    "CalendarSettings",
    "CloudTasksSettings",
    "DedupeBackend",
    "DedupeSettings",
    "Environment",
    # Infrastructure
    "FirestoreSettings",
    "FloodDetectionSettings",
    "GCSSettings",
    "InboundLogSettings",
    "LogBackend",
    # AI
    "OpenAISettings",
    "PubSubSettings",
    "QueueBackend",
    "SessionSettings",
    "SessionStoreBackend",
    # Channels
    "WhatsAppSettings",
    "get_base_settings",
    "get_calendar_settings",
    "get_cloud_tasks_settings",
    "get_dedupe_settings",
    "get_firestore_settings",
    "get_flood_detection_settings",
    "get_gcs_settings",
    "get_inbound_log_settings",
    "get_openai_settings",
    "get_pubsub_settings",
    "get_session_settings",
    "get_whatsapp_settings",
]
