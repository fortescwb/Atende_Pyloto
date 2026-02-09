"""Factories de stores e infra baseadas em configuração de ambiente."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from app.bootstrap.clients import (
    create_async_redis_client,
    create_firestore_client,
    create_redis_client,
)
from app.infra.stores import (
    FirestoreAuditStore,
    FirestoreContactCardStore,
    MemoryAuditStore,
    MemoryContactCardStore,
    MemoryDedupeStore,
    MemorySessionStore,
    RedisContactCardStore,
    RedisDedupeStore,
    RedisSessionStore,
)
from app.protocols.dedupe import AsyncDedupeProtocol, DedupeProtocol
from app.protocols.session_store import AsyncSessionStoreProtocol, SessionStoreProtocol

if TYPE_CHECKING:
    from app.protocols.contact_card_store import ContactCardStoreProtocol
    from app.protocols.decision_audit_store import DecisionAuditStoreProtocol

logger = logging.getLogger(__name__)


def _runtime_environment() -> str:
    return os.getenv("ENVIRONMENT", "development").lower()


def _default_backend_for_env(environment: str) -> str:
    return "redis" if environment in ("staging", "production") else "memory"


def create_session_store() -> SessionStoreProtocol:
    """Cria store de sessão baseado na configuração."""
    environment = _runtime_environment()
    backend = os.getenv("SESSION_STORE_BACKEND", _default_backend_for_env(environment)).lower()

    if backend == "redis":
        redis_client = create_redis_client()
        try:
            async_client = create_async_redis_client()
        except Exception:
            async_client = None
        store = RedisSessionStore(redis_client, async_client)
        logger.info("session_store_created", extra={"backend": "redis"})
        return store

    if backend == "memory":
        if environment not in ("development", "test"):
            logger.warning(
                "memory_store_in_non_dev",
                extra={"backend": "memory", "environment": environment},
            )
        store = MemorySessionStore()
        logger.info("session_store_created", extra={"backend": "memory"})
        return store

    msg = f"SESSION_STORE_BACKEND inválido: {backend}"
    raise ValueError(msg)


def create_async_session_store() -> AsyncSessionStoreProtocol:
    """Cria store de sessão assíncrono."""
    store = create_session_store()
    if not isinstance(store, AsyncSessionStoreProtocol):
        msg = "Store não suporta operações assíncronas"
        raise TypeError(msg)
    return store


def create_dedupe_store() -> DedupeProtocol:
    """Cria store de dedupe baseado na configuração."""
    environment = _runtime_environment()
    backend = os.getenv("DEDUPE_BACKEND", _default_backend_for_env(environment)).lower()

    if backend == "redis":
        redis_client = create_redis_client()
        try:
            async_client = create_async_redis_client()
        except Exception:
            async_client = None
        store = RedisDedupeStore(redis_client, async_client)
        logger.info("dedupe_store_created", extra={"backend": "redis"})
        return store

    if backend == "memory":
        if environment not in ("development", "test"):
            logger.warning(
                "memory_dedupe_in_non_dev",
                extra={"backend": "memory", "environment": environment},
            )
        store = MemoryDedupeStore()
        logger.info("dedupe_store_created", extra={"backend": "memory"})
        return store

    msg = f"DEDUPE_BACKEND inválido: {backend}"
    raise ValueError(msg)


def create_async_dedupe_store() -> AsyncDedupeProtocol:
    """Cria store de dedupe assíncrono."""
    store = create_dedupe_store()
    if not isinstance(store, AsyncDedupeProtocol):
        msg = "Store não suporta operações assíncronas"
        raise TypeError(msg)
    return store


def create_audit_store() -> DecisionAuditStoreProtocol:
    """Cria store de auditoria baseado na configuração."""
    backend = os.getenv("AUDIT_STORE_BACKEND", "memory").lower()
    if backend == "firestore":
        firestore_client = create_firestore_client()
        store = FirestoreAuditStore(firestore_client)
        logger.info("audit_store_created", extra={"backend": "firestore"})
        return store
    if backend == "memory":
        store = MemoryAuditStore()
        logger.info("audit_store_created", extra={"backend": "memory"})
        return store
    msg = f"AUDIT_STORE_BACKEND inválido: {backend}"
    raise ValueError(msg)


def create_contact_card_store() -> ContactCardStoreProtocol:
    """Cria store de ContactCard baseado na configuração."""
    environment = _runtime_environment()
    default_backend = "firestore" if environment in ("staging", "production") else "memory"
    backend = os.getenv("CONTACT_CARD_BACKEND") or os.getenv("LEAD_PROFILE_BACKEND")
    backend = (backend or default_backend).lower()

    if backend == "firestore":
        firestore_client = create_firestore_client()
        store = FirestoreContactCardStore(firestore_client)
        logger.info("contact_card_store_created", extra={"backend": "firestore"})
        return store

    if backend == "redis":
        redis_client = create_redis_client()
        try:
            async_client = create_async_redis_client()
        except Exception:
            async_client = None
        store = RedisContactCardStore(redis_client, async_client)
        logger.info("contact_card_store_created", extra={"backend": "redis"})
        return store

    if backend == "memory":
        if environment not in ("development", "test"):
            logger.warning(
                "memory_contact_card_in_non_dev",
                extra={"backend": "memory", "environment": environment},
            )
        store = MemoryContactCardStore()
        logger.info("contact_card_store_created", extra={"backend": "memory"})
        return store

    msg = f"CONTACT_CARD_BACKEND invalido: {backend}"
    raise ValueError(msg)
