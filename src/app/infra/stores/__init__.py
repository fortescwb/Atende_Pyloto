"""Stores — implementações concretas de persistência.

Módulos disponíveis:
    - redis_session_store: Store de sessão usando Redis (Upstash)
    - redis_dedupe_store: Store de dedupe usando Redis (Upstash)
    - firestore_audit_store: Store de auditoria usando Firestore
    - firestore_conversation_store: Store de conversas usando Firestore
    - contact_card_store: Store de ContactCard (Memory/Redis)
    - firestore_contact_card_store: Store de ContactCard (Firestore)
    - memory_stores: Stores em memória para desenvolvimento/testes
"""

from __future__ import annotations

from app.infra.stores.contact_card_store import (
    MemoryContactCardStore,
    RedisContactCardStore,
)
from app.infra.stores.firestore_audit_store import FirestoreAuditStore
from app.infra.stores.firestore_contact_card_store import FirestoreContactCardStore
from app.infra.stores.firestore_conversation_store import FirestoreConversationStore
from app.infra.stores.memory_stores import (
    MemoryAuditStore,
    MemoryDedupeStore,
    MemorySessionStore,
)
from app.infra.stores.redis_dedupe_store import RedisDedupeStore
from app.infra.stores.redis_session_store import RedisSessionStore

__all__ = [
    "FirestoreAuditStore",
    "FirestoreContactCardStore",
    "FirestoreConversationStore",
    "MemoryAuditStore",
    "MemoryContactCardStore",
    "MemoryDedupeStore",
    "MemorySessionStore",
    "RedisContactCardStore",
    "RedisDedupeStore",
    "RedisSessionStore",
]
