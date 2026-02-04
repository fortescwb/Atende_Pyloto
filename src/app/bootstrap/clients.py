"""Factories de clientes externos — Redis e Firestore.

Módulo extraído de dependencies.py para respeitar limite de 200 linhas.

Referência: REGRAS_E_PADROES.md § 4 — Limites de tamanho
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from google.cloud.firestore import Client as FirestoreClient
    from redis import Redis
    from redis.asyncio import Redis as AsyncRedis

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Redis Client Factories
# ──────────────────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def create_redis_client() -> Redis[bytes]:
    """Cria cliente Redis síncrono (singleton).

    Usa REDIS_URL da env ou Secret Manager via Cloud Run.

    Returns:
        Cliente Redis configurado

    Raises:
        ValueError: Se REDIS_URL não configurado
    """
    import redis

    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        msg = "REDIS_URL não configurado"
        raise ValueError(msg)

    client: Redis[bytes] = redis.from_url(
        redis_url,
        decode_responses=False,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
        retry_on_timeout=True,
    )

    host = client.connection_pool.connection_kwargs.get("host", "unknown")
    logger.info("redis_client_created", extra={"host": host})
    return client


@lru_cache(maxsize=1)
def create_async_redis_client() -> AsyncRedis[bytes]:
    """Cria cliente Redis assíncrono (singleton).

    Returns:
        Cliente Redis assíncrono

    Raises:
        ValueError: Se REDIS_URL não configurado
    """
    from redis.asyncio import Redis as AsyncRedis

    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        msg = "REDIS_URL não configurado"
        raise ValueError(msg)

    client: AsyncRedis[bytes] = AsyncRedis.from_url(
        redis_url,
        decode_responses=False,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
    )

    logger.info("async_redis_client_created")
    return client


# ──────────────────────────────────────────────────────────────────────────────
# Firestore Client Factory
# ──────────────────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def create_firestore_client() -> FirestoreClient:
    """Cria cliente Firestore (singleton).

    Returns:
        Cliente Firestore
    """
    from google.cloud import firestore

    project_id = os.getenv("GCP_PROJECT") or os.getenv("FIRESTORE_PROJECT_ID")
    client = firestore.Client(project=project_id)
    logger.info("firestore_client_created", extra={"project": project_id})
    return client
