"""Redis Session Store — implementação com Upstash Redis.

Store de sessão otimizado para alta concorrência (centenas de req/s).
Usa operações atômicas do Redis para evitar race conditions.

Referência: FUNCIONAMENTO.md § 6 — Concorrência e escalabilidade
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from app.protocols.session_store import AsyncSessionStoreProtocol, SessionStoreProtocol
from app.sessions.models import Session

if TYPE_CHECKING:
    from redis import Redis
    from redis.asyncio import Redis as AsyncRedis

logger = logging.getLogger(__name__)

# Prefixo para namespace de sessões
SESSION_PREFIX = "session:"


class RedisSessionStore(SessionStoreProtocol, AsyncSessionStoreProtocol):
    """Store de sessão usando Redis (Upstash compatível).

    Características:
        - Operações atômicas (SET NX, SETEX)
        - TTL automático por sessão
        - Suporte sync e async
        - Compatível com Upstash Redis (REST API)

    Args:
        redis_client: Cliente Redis síncrono
        async_redis_client: Cliente Redis assíncrono (opcional)
    """

    def __init__(
        self,
        redis_client: Redis[bytes],
        async_redis_client: AsyncRedis[bytes] | None = None,
    ) -> None:
        self._redis = redis_client
        self._async_redis = async_redis_client

    def _key(self, session_id: str) -> str:
        """Gera chave Redis com namespace."""
        return f"{SESSION_PREFIX}{session_id}"

    # ──────────────────────────────────────────────────────────────
    # Sync API
    # ──────────────────────────────────────────────────────────────

    def save(self, session: Any, ttl_seconds: int = 7200) -> None:
        """Salva sessão no Redis com TTL."""
        if isinstance(session, Session):
            data = json.dumps(session.to_dict())
            session_id = session.session_id
        else:
            data = json.dumps(session)
            session_id = session.get("session_id", "")

        key = self._key(session_id)
        self._redis.setex(key, ttl_seconds, data)
        logger.debug("session_saved", extra={"session_id": session_id, "ttl": ttl_seconds})

    def load(self, session_id: str) -> Session | None:
        """Carrega sessão do Redis."""
        key = self._key(session_id)
        data = self._redis.get(key)
        if data is None:
            return None
        try:
            return Session.from_dict(json.loads(data))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("session_load_error", extra={"session_id": session_id, "error": str(e)})
            return None

    def delete(self, session_id: str) -> bool:
        """Remove sessão do Redis."""
        key = self._key(session_id)
        result = self._redis.delete(key)
        return bool(result)

    def exists(self, session_id: str) -> bool:
        """Verifica se sessão existe no Redis."""
        key = self._key(session_id)
        return bool(self._redis.exists(key))

    # ──────────────────────────────────────────────────────────────
    # Async API
    # ──────────────────────────────────────────────────────────────

    async def save_async(self, session: Any, ttl_seconds: int = 7200) -> None:
        """Salva sessão no Redis com TTL (async)."""
        if self._async_redis is None:
            msg = "Async Redis client não configurado"
            raise RuntimeError(msg)

        if isinstance(session, Session):
            data = json.dumps(session.to_dict())
            session_id = session.session_id
        else:
            data = json.dumps(session)
            session_id = session.get("session_id", "")

        key = self._key(session_id)
        await self._async_redis.setex(key, ttl_seconds, data)
        logger.debug("session_saved_async", extra={"session_id": session_id, "ttl": ttl_seconds})

    async def load_async(self, session_id: str) -> Session | None:
        """Carrega sessão do Redis (async)."""
        if self._async_redis is None:
            msg = "Async Redis client não configurado"
            raise RuntimeError(msg)

        key = self._key(session_id)
        data = await self._async_redis.get(key)
        if data is None:
            return None
        try:
            return Session.from_dict(json.loads(data))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(
                "session_load_error_async", extra={"session_id": session_id, "error": str(e)}
            )
            return None

    async def delete_async(self, session_id: str) -> bool:
        """Remove sessão do Redis (async)."""
        if self._async_redis is None:
            msg = "Async Redis client não configurado"
            raise RuntimeError(msg)

        key = self._key(session_id)
        result = await self._async_redis.delete(key)
        return bool(result)

    async def exists_async(self, session_id: str) -> bool:
        """Verifica se sessão existe no Redis (async)."""
        if self._async_redis is None:
            msg = "Async Redis client não configurado"
            raise RuntimeError(msg)

        key = self._key(session_id)
        return bool(await self._async_redis.exists(key))
