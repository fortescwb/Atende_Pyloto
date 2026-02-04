"""Agregador de settings de infraestrutura GCP.

Re-exporta todas as settings de infraestrutura para uso externo.
"""

from __future__ import annotations

from config.settings.infra.cloud_tasks import (
    CloudTasksSettings,
    QueueBackend,
    get_cloud_tasks_settings,
)
from config.settings.infra.firestore import (
    FirestoreSettings,
    get_firestore_settings,
)
from config.settings.infra.gcs import (
    GCSSettings,
    get_gcs_settings,
)
from config.settings.infra.inbound_log import (
    InboundLogSettings,
    LogBackend,
    get_inbound_log_settings,
)
from config.settings.infra.pubsub import (
    PubSubSettings,
    get_pubsub_settings,
)

__all__ = [
    # Cloud Tasks
    "CloudTasksSettings",
    # Firestore
    "FirestoreSettings",
    # GCS
    "GCSSettings",
    # Inbound Log
    "InboundLogSettings",
    "LogBackend",
    # Pub/Sub
    "PubSubSettings",
    # Types
    "QueueBackend",
    "get_cloud_tasks_settings",
    "get_firestore_settings",
    "get_gcs_settings",
    "get_inbound_log_settings",
    "get_pubsub_settings",
]
