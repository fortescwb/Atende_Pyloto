"""Factories de stores — criação de implementações concretas.

Este módulo centraliza a criação de stores baseadas nas
configurações de ambiente.

Referência: REGRAS_E_PADROES.md § 2.3 — app/bootstrap
"""

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


# ──────────────────────────────────────────────────────────────────────────────
# Session Store Factory
# ──────────────────────────────────────────────────────────────────────────────


def create_session_store() -> SessionStoreProtocol:
    """Cria store de sessão baseado na configuração.

    Lê SESSION_STORE_BACKEND da env:
    - "memory": MemorySessionStore (dev only)
    - "redis": RedisSessionStore (staging/production)
    - "firestore": (não implementado ainda)

    Returns:
        Implementação de SessionStoreProtocol
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
    default_backend = "redis" if environment in ("staging", "production") else "memory"
    backend = os.getenv("SESSION_STORE_BACKEND", default_backend).lower()

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


# ──────────────────────────────────────────────────────────────────────────────
# Dedupe Store Factory
# ──────────────────────────────────────────────────────────────────────────────


def create_dedupe_store() -> DedupeProtocol:
    """Cria store de dedupe baseado na configuração.

    Lê DEDUPE_BACKEND da env:
    - "memory": MemoryDedupeStore (dev only)
    - "redis": RedisDedupeStore (staging/production)

    Returns:
        Implementação de DedupeProtocol
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
    default_backend = "redis" if environment in ("staging", "production") else "memory"
    backend = os.getenv("DEDUPE_BACKEND", default_backend).lower()

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


# ──────────────────────────────────────────────────────────────────────────────
# Audit Store Factory
# ──────────────────────────────────────────────────────────────────────────────


def create_audit_store() -> DecisionAuditStoreProtocol:
    """Cria store de auditoria baseado na configuração.

    Lê AUDIT_STORE_BACKEND da env:
    - "memory": MemoryAuditStore (dev only)
    - "firestore": FirestoreAuditStore (staging/production)

    Returns:
        Implementação de DecisionAuditStoreProtocol
    """
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


# ──────────────────────────────────────────────────────────────────────────────
# AI Orchestrator Factory
# ──────────────────────────────────────────────────────────────────────────────


def create_ai_orchestrator():
    """Cria AIOrchestrator com client OpenAI configurado.

    Retorna:
        AIOrchestrator com OpenAIClient injetado
    """
    from ai.services.orchestrator import AIOrchestrator
    from app.infra.ai.openai_client import OpenAIClient

    client = OpenAIClient()
    orchestrator = AIOrchestrator(client=client)
    logger.info("ai_orchestrator_created")
    return orchestrator


# ──────────────────────────────────────────────────────────────────────────────
# Otto Agent Factory
# ──────────────────────────────────────────────────────────────────────────────


def create_otto_agent_service():
    """Cria OttoAgentService com client OpenAI configurado."""
    from ai.services.otto_agent import OttoAgentService
    from app.infra.ai.otto_client import OttoClient

    client = OttoClient()
    service = OttoAgentService(client=client)
    logger.info("otto_agent_service_created")
    return service


# ──────────────────────────────────────────────────────────────────────────────
# ContactCard Store Factory
# ──────────────────────────────────────────────────────────────────────────────


def create_contact_card_store() -> ContactCardStoreProtocol:
    """Cria store de ContactCard baseado na configuracao.

    Lê CONTACT_CARD_BACKEND da env (fallback para LEAD_PROFILE_BACKEND):
    - "firestore": FirestoreContactCardStore (staging/production)
    - "redis": RedisContactCardStore (opcional)
    - "memory": MemoryContactCardStore (dev/test)
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
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


# ──────────────────────────────────────────────────────────────────────────────
# ContactCardExtractor Factory
# ──────────────────────────────────────────────────────────────────────────────


def create_contact_card_extractor_service():
    """Cria ContactCardExtractorService com client OpenAI."""
    from ai.services.contact_card_extractor import ContactCardExtractorService
    from app.infra.ai.contact_card_extractor_client import ContactCardExtractorClient

    client = ContactCardExtractorClient()
    service = ContactCardExtractorService(client=client)
    logger.info("contact_card_extractor_service_created")
    return service


# ──────────────────────────────────────────────────────────────────────────────
# Transcription Service Factory
# ──────────────────────────────────────────────────────────────────────────────


def create_transcription_service():
    """Cria TranscriptionAgent com dependencias padrao."""
    from app.services.transcription_agent import TranscriptionAgent

    service = TranscriptionAgent()
    logger.info("transcription_service_created")
    return service
