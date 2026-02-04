"""Firestore Audit Store — auditoria de decisões.

Store para persistir decisões de IA e transições de FSM.
Otimizado para append-only com TTL configurável.

Referência: FUNCIONAMENTO.md § 8 — Observabilidade e auditoria
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.protocols.decision_audit_store import DecisionAuditStoreProtocol

if TYPE_CHECKING:
    from google.cloud.firestore import Client as FirestoreClient

logger = logging.getLogger(__name__)

# Collection para auditoria
AUDIT_COLLECTION = "decision_audit"


class FirestoreAuditStore(DecisionAuditStoreProtocol):
    """Store de auditoria usando Firestore.

    Características:
        - Append-only (sem updates)
        - Particionado por tenant/dia para queries eficientes
        - TTL via Firestore TTL policies
        - Sem PII nos registros

    Args:
        firestore_client: Cliente Firestore
        collection_name: Nome da collection (default: decision_audit)
    """

    def __init__(
        self,
        firestore_client: FirestoreClient,
        collection_name: str = AUDIT_COLLECTION,
    ) -> None:
        self._db = firestore_client
        self._collection = collection_name

    def append(self, record: dict[str, Any]) -> None:
        """Append de registro de auditoria.

        O registro é enriquecido com timestamp e organizado por tenant/dia.

        Args:
            record: Registro de auditoria (sem PII)
        """
        now = datetime.now(UTC)

        # Enriquecer registro
        enriched = {
            **record,
            "timestamp": now.isoformat(),
            "created_at": now,  # Para TTL do Firestore
        }

        # Gerar document ID único
        tenant_id = record.get("tenant_id", "default")
        session_id = record.get("session_id", "unknown")
        doc_id = f"{tenant_id}_{now.strftime('%Y%m%d')}_{session_id}_{now.timestamp()}"

        try:
            self._db.collection(self._collection).document(doc_id).set(enriched)
            logger.debug(
                "audit_record_appended",
                extra={
                    "doc_id": doc_id,
                    "event_type": record.get("event_type", "unknown"),
                },
            )
        except Exception as e:
            # Não falhar o fluxo principal por erro de auditoria
            logger.error(
                "audit_append_error",
                extra={"error": str(e), "doc_id": doc_id},
            )

    async def append_async(self, record: dict[str, Any]) -> None:
        """Append assíncrono de registro de auditoria.

        Usa asyncio.to_thread para não bloquear o event loop,
        já que Firestore Python SDK não tem async nativo.

        Args:
            record: Registro de auditoria (sem PII)
        """
        await asyncio.to_thread(self.append, record)
