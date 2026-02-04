"""Settings do Firestore.

Configurações para Google Cloud Firestore.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class FirestoreSettings:
    """Configurações do Firestore.

    Attributes:
        project_id: ID do projeto GCP (usa GCP_PROJECT se não definido)
        collection_sessions: Collection para sessões
        collection_messages: Collection para mensagens
        collection_dedupe: Collection para dedupe
        collection_audit: Collection para auditoria
    """

    project_id: str = ""
    collection_sessions: str = "sessions"
    collection_messages: str = "messages"
    collection_dedupe: str = "dedupe"
    collection_audit: str = "audit"

    def validate(self, gcp_project: str) -> list[str]:
        """Valida configurações do Firestore.

        Args:
            gcp_project: Projeto GCP padrão para fallback.

        Returns:
            Lista de erros de validação.
        """
        errors: list[str] = []
        effective_project = self.project_id or gcp_project

        if not effective_project:
            errors.append(
                "FIRESTORE_PROJECT_ID ou GCP_PROJECT deve estar configurado"
            )

        return errors


def _load_firestore_from_env() -> FirestoreSettings:
    """Carrega FirestoreSettings de variáveis de ambiente."""
    return FirestoreSettings(
        project_id=os.getenv("FIRESTORE_PROJECT_ID", ""),
        collection_sessions=os.getenv("FIRESTORE_COLLECTION_SESSIONS", "sessions"),
        collection_messages=os.getenv("FIRESTORE_COLLECTION_MESSAGES", "messages"),
        collection_dedupe=os.getenv("FIRESTORE_COLLECTION_DEDUPE", "dedupe"),
        collection_audit=os.getenv("FIRESTORE_COLLECTION_AUDIT", "audit"),
    )


@lru_cache(maxsize=1)
def get_firestore_settings() -> FirestoreSettings:
    """Retorna instância cacheada de FirestoreSettings."""
    return _load_firestore_from_env()
