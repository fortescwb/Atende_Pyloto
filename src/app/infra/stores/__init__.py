"""Stores — implementações concretas de persistência.

Módulos disponíveis:
    - redis_session_store: Store de sessão usando Redis (Upstash)
    - redis_dedupe_store: Store de dedupe usando Redis (Upstash)
    - firestore_audit_store: Store de auditoria usando Firestore
    - memory_stores: Stores em memória para desenvolvimento/testes
"""

from __future__ import annotations

from app.infra.stores.firestore_audit_store import FirestoreAuditStore
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
    "MemoryAuditStore",
    "MemoryDedupeStore",
    # Memory (dev/test)
    "MemorySessionStore",
    "RedisDedupeStore",
    # Redis (Upstash)
    "RedisSessionStore",
]
