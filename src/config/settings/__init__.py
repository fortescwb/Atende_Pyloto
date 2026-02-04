"""Agregador de settings do Atende_Pyloto.

Re-exporta todas as settings e funções de cada módulo.
Organização por domínio para isolamento de mudanças.
"""

from __future__ import annotations

# AI/LLM settings
from config.settings.ai import (
    AuditBackend,
    FloodDetectionSettings,
    MasterDeciderSettings,
    OpenAISettings,
    ResponseGeneratorSettings,
    StateSelectorSettings,
    get_flood_detection_settings,
    get_master_decider_settings,
    get_openai_settings,
    get_response_generator_settings,
    get_state_selector_settings,
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
    # Types
    "AuditBackend",
    # Base
    "BaseSettings",
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
    "MasterDeciderSettings",
    # AI
    "OpenAISettings",
    "PubSubSettings",
    "QueueBackend",
    "ResponseGeneratorSettings",
    "SessionSettings",
    "SessionStoreBackend",
    "StateSelectorSettings",
    # Channels
    "WhatsAppSettings",
    "get_base_settings",
    "get_cloud_tasks_settings",
    "get_dedupe_settings",
    "get_firestore_settings",
    "get_flood_detection_settings",
    "get_gcs_settings",
    "get_inbound_log_settings",
    "get_master_decider_settings",
    "get_openai_settings",
    "get_pubsub_settings",
    "get_response_generator_settings",
    "get_session_settings",
    "get_state_selector_settings",
    "get_whatsapp_settings",
]
