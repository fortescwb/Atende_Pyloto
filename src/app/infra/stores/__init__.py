"""Stores — implementações concretas de persistência.

Módulos disponíveis:
    - redis_session_store: Store de sessão usando Redis (Upstash)
    - redis_dedupe_store: Store de dedupe usando Redis (Upstash)
    - firestore_audit_store: Store de auditoria usando Firestore
    - firestore_conversation_store: Store de conversas usando Firestore
    - lead_profile_store: Store de LeadProfile (Memory/Redis)
    - memory_stores: Stores em memória para desenvolvimento/testes
"""

from __future__ import annotations

from app.infra.stores.firestore_audit_store import FirestoreAuditStore
from app.infra.stores.firestore_conversation_store import FirestoreConversationStore
from app.infra.stores.lead_profile_store import (
    MemoryLeadProfileStore,
    RedisLeadProfileStore,
)
from app.infra.stores.memory_stores import (
    MemoryAuditStore,
    MemoryDedupeStore,
    MemorySessionStore,
)
from app.infra.stores.redis_dedupe_store import RedisDedupeStore
from app.infra.stores.redis_session_store import RedisSessionStore

__all__ = [
    # Firestore
    "FirestoreAuditStore",
    "FirestoreConversationStore",
    # LeadProfile
    "MemoryLeadProfileStore",
    "RedisLeadProfileStore",
    # Memory (dev/test)
    "MemoryAuditStore",
    "MemoryDedupeStore",
    "MemorySessionStore",
    # Redis (Upstash)
    "RedisDedupeStore",
    "RedisSessionStore",
]
