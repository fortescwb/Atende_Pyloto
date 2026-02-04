"""Settings do Pub/Sub.

Configurações para Google Cloud Pub/Sub.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class PubSubSettings:
    """Configurações do Pub/Sub.

    Attributes:
        topic_inbound: Tópico para mensagens inbound
        topic_outbound: Tópico para mensagens outbound
        topic_handoff: Tópico para handoff de conversas
        topic_audit: Tópico para eventos de auditoria
    """

    topic_inbound: str = "whatsapp-inbound"
    topic_outbound: str = "whatsapp-outbound"
    topic_handoff: str = "whatsapp-handoff"
    topic_audit: str = "audit-events"

    def validate(self) -> list[str]:
        """Valida configurações do Pub/Sub.

        Returns:
            Lista de erros de validação.
        """
        # Tópicos têm defaults, então são sempre válidos
        # Validação real ocorre ao tentar publicar
        return []


def _load_pubsub_from_env() -> PubSubSettings:
    """Carrega PubSubSettings de variáveis de ambiente."""
    return PubSubSettings(
        topic_inbound=os.getenv("PUBSUB_TOPIC_INBOUND", "whatsapp-inbound"),
        topic_outbound=os.getenv("PUBSUB_TOPIC_OUTBOUND", "whatsapp-outbound"),
        topic_handoff=os.getenv("PUBSUB_TOPIC_HANDOFF", "whatsapp-handoff"),
        topic_audit=os.getenv("PUBSUB_TOPIC_AUDIT", "audit-events"),
    )


@lru_cache(maxsize=1)
def get_pubsub_settings() -> PubSubSettings:
    """Retorna instância cacheada de PubSubSettings."""
    return _load_pubsub_from_env()
