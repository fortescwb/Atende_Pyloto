"""Redis Dedupe Store — deduplicação com Upstash Redis.

Store de deduplicação otimizado para alta concorrência.
Usa SET NX (set if not exists) para operação atômica.

Contrato de Keys:
    As keys devem ser IDs opacos ou hashes (ex.: message_id, SHA256).
    NUNCA passar dados sensíveis (PII, telefones, emails) como key.
    Keys são logadas parcialmente em DEBUG; dados sensíveis vazariam.

Referência: FUNCIONAMENTO.md § 4.3 — Dedupe + Anti-abuso
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.protocols.dedupe import AsyncDedupeProtocol, DedupeProtocol

if TYPE_CHECKING:
    from redis import Redis
    from redis.asyncio import Redis as AsyncRedis

logger = logging.getLogger(__name__)

# Prefixo para namespace de dedupe
DEDUPE_PREFIX = "dedupe:"


class RedisDedupeStore(DedupeProtocol, AsyncDedupeProtocol):
    """Store de dedupe usando Redis (Upstash compatível).

    Usa SET NX (set if not exists) para garantir atomicidade.
    Ideal para processar centenas de mensagens simultâneas sem duplicatas.

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

    def _key(self, key: str) -> str:
        """Gera chave Redis com namespace."""
        return f"{DEDUPE_PREFIX}{key}"

    # ──────────────────────────────────────────────────────────────
    # Sync API (DedupeProtocol)
    # ──────────────────────────────────────────────────────────────

    def seen(self, key: str, ttl: int) -> bool:
        """Verifica e marca chave atomicamente.

        Usa SET NX EX para operação atômica:
        - Se chave não existe: cria com TTL e retorna False (novo)
        - Se chave existe: retorna True (duplicado)

        Args:
            key: Chave única (ex.: message_id)
            ttl: TTL em segundos

        Returns:
            True se duplicado, False se novo
        """
        redis_key = self._key(key)
        # SET NX retorna True se criou (novo), False se já existia (duplicado)
        was_set = self._redis.set(redis_key, "1", nx=True, ex=ttl)
        is_duplicate = not was_set
        if is_duplicate:
            key_masked = key[:8] + "..." if len(key) > 8 else key
            logger.debug("dedupe_duplicate_detected", extra={"key": key_masked})
        return is_duplicate

    # ──────────────────────────────────────────────────────────────
    # Async API (AsyncDedupeProtocol)
    # ──────────────────────────────────────────────────────────────

    async def is_duplicate(self, key: str, ttl: int = 3600) -> bool:
        """Verifica se chave já foi processada (async).

        Args:
            key: Chave única (ex.: message_id)
            ttl: TTL padrão (não usado na verificação, apenas para compatibilidade)

        Returns:
            True se duplicado, False se novo
        """
        if self._async_redis is None:
            msg = "Async Redis client não configurado"
            raise RuntimeError(msg)

        redis_key = self._key(key)
        return bool(await self._async_redis.exists(redis_key))

    async def mark_processed(self, key: str, ttl: int = 3600) -> None:
        """Marca chave como processada (async).

        Args:
            key: Chave única (ex.: message_id)
            ttl: TTL em segundos
        """
        if self._async_redis is None:
            msg = "Async Redis client não configurado"
            raise RuntimeError(msg)

        redis_key = self._key(key)
        await self._async_redis.setex(redis_key, ttl, "1")
        key_masked = key[:8] + "..." if len(key) > 8 else key
        logger.debug("dedupe_marked_async", extra={"key": key_masked, "ttl": ttl})

    async def seen_async(self, key: str, ttl: int) -> bool:
        """Verifica e marca chave atomicamente (async).

        Versão async do método `seen` usando SET NX.

        Args:
            key: Chave única
            ttl: TTL em segundos

        Returns:
            True se duplicado, False se novo
        """
        if self._async_redis is None:
            msg = "Async Redis client não configurado"
            raise RuntimeError(msg)

        redis_key = self._key(key)
        was_set = await self._async_redis.set(redis_key, "1", nx=True, ex=ttl)
        is_duplicate = not was_set
        if is_duplicate:
            key_masked = key[:8] + "..." if len(key) > 8 else key
            logger.debug("dedupe_duplicate_detected_async", extra={"key": key_masked})
        return is_duplicate
