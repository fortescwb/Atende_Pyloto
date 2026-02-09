"""Testes do RedisDedupeStore com mock."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infra.stores.redis_dedupe_store import RedisDedupeStore
from utils.errors import RedisConnectionError


class TestRedisDedupeStore:
    """Testes do RedisDedupeStore."""

    def test_seen_returns_false_for_new(self) -> None:
        """Deve retornar False quando chave é nova (SET NX retorna True)."""
        mock_redis = MagicMock()
        mock_redis.set.return_value = True  # SET NX criou a chave
        store = RedisDedupeStore(mock_redis)

        result = store.seen("new-key", ttl=3600)

        assert result is False  # Não é duplicado
        mock_redis.set.assert_called_once_with(
            "dedupe:new-key", "1", nx=True, ex=3600
        )

    def test_seen_returns_true_for_duplicate(self) -> None:
        """Deve retornar True quando chave já existe (SET NX retorna False)."""
        mock_redis = MagicMock()
        mock_redis.set.return_value = False  # SET NX não criou (já existe)
        store = RedisDedupeStore(mock_redis)

        result = store.seen("dup-key", ttl=3600)

        assert result is True  # É duplicado

    def test_key_has_namespace(self) -> None:
        """Deve usar prefixo dedupe: nas chaves."""
        mock_redis = MagicMock()
        mock_redis.set.return_value = True
        store = RedisDedupeStore(mock_redis)

        store.seen("my-message-id", ttl=600)

        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "dedupe:my-message-id"

    @pytest.mark.anyio
    async def test_is_duplicate_checks_processed_and_processing(self) -> None:
        """is_duplicate deve considerar chave processada e lock de processamento."""
        async_redis = MagicMock()
        pipeline = MagicMock()
        pipeline.exists.return_value = pipeline
        pipeline.execute = AsyncMock(return_value=[0, 1])
        async_redis.pipeline.return_value = pipeline

        store = RedisDedupeStore(MagicMock(), async_redis)

        result = await store.is_duplicate("msg-1")

        assert result is True
        pipeline.exists.assert_any_call("dedupe:msg-1")
        pipeline.exists.assert_any_call("dedupe:processing:msg-1")
        pipeline.execute.assert_awaited_once()

    @pytest.mark.anyio
    async def test_mark_processing_sets_ttl(self) -> None:
        """mark_processing deve criar lock temporário."""
        async_redis = MagicMock()
        async_redis.setex = AsyncMock()
        store = RedisDedupeStore(MagicMock(), async_redis)

        await store.mark_processing("msg-2", ttl=45)

        async_redis.setex.assert_awaited_once_with("dedupe:processing:msg-2", 45, "1")

    @pytest.mark.anyio
    async def test_mark_processed_promotes_and_clears_processing_lock(self) -> None:
        """mark_processed deve salvar dedupe final e remover lock temporário."""
        async_redis = MagicMock()
        pipeline = MagicMock()
        pipeline.setex.return_value = pipeline
        pipeline.delete.return_value = pipeline
        pipeline.execute = AsyncMock()
        async_redis.pipeline.return_value = pipeline

        store = RedisDedupeStore(MagicMock(), async_redis)

        await store.mark_processed("msg-3", ttl=3600)

        pipeline.setex.assert_called_once_with("dedupe:msg-3", 3600, "1")
        pipeline.delete.assert_called_once_with("dedupe:processing:msg-3")
        pipeline.execute.assert_awaited_once()

    @pytest.mark.anyio
    async def test_unmark_processing_removes_lock(self) -> None:
        """unmark_processing deve liberar lock para retry."""
        async_redis = MagicMock()
        async_redis.delete = AsyncMock()
        store = RedisDedupeStore(MagicMock(), async_redis)

        await store.unmark_processing("msg-4")

        async_redis.delete.assert_awaited_once_with("dedupe:processing:msg-4")

    @pytest.mark.anyio
    async def test_is_duplicate_raises_without_async_client(self) -> None:
        store = RedisDedupeStore(MagicMock(), None)

        with pytest.raises(RuntimeError, match="Async Redis client"):
            await store.is_duplicate("msg-5")

    @pytest.mark.anyio
    async def test_is_duplicate_wraps_pipeline_errors(self) -> None:
        async_redis = MagicMock()
        pipeline = MagicMock()
        pipeline.exists.return_value = pipeline
        pipeline.execute = AsyncMock(side_effect=Exception("redis down"))
        async_redis.pipeline.return_value = pipeline
        store = RedisDedupeStore(MagicMock(), async_redis)

        with pytest.raises(RedisConnectionError, match="consultar dedupe"):
            await store.is_duplicate("msg-5")

    @pytest.mark.anyio
    async def test_mark_processing_raises_without_async_client(self) -> None:
        store = RedisDedupeStore(MagicMock(), None)

        with pytest.raises(RuntimeError, match="Async Redis client"):
            await store.mark_processing("msg-6")

    @pytest.mark.anyio
    async def test_mark_processing_wraps_redis_errors(self) -> None:
        async_redis = MagicMock()
        async_redis.setex = AsyncMock(side_effect=Exception("redis down"))
        store = RedisDedupeStore(MagicMock(), async_redis)

        with pytest.raises(RedisConnectionError, match="marcar processamento"):
            await store.mark_processing("msg-6")

    @pytest.mark.anyio
    async def test_mark_processed_raises_without_async_client(self) -> None:
        store = RedisDedupeStore(MagicMock(), None)

        with pytest.raises(RuntimeError, match="Async Redis client"):
            await store.mark_processed("msg-7")

    @pytest.mark.anyio
    async def test_mark_processed_wraps_pipeline_errors(self) -> None:
        async_redis = MagicMock()
        pipeline = MagicMock()
        pipeline.setex.return_value = pipeline
        pipeline.delete.return_value = pipeline
        pipeline.execute = AsyncMock(side_effect=Exception("redis down"))
        async_redis.pipeline.return_value = pipeline
        store = RedisDedupeStore(MagicMock(), async_redis)

        with pytest.raises(RedisConnectionError, match="concluir dedupe"):
            await store.mark_processed("msg-7")

    @pytest.mark.anyio
    async def test_unmark_processing_raises_without_async_client(self) -> None:
        store = RedisDedupeStore(MagicMock(), None)

        with pytest.raises(RuntimeError, match="Async Redis client"):
            await store.unmark_processing("msg-8")

    @pytest.mark.anyio
    async def test_unmark_processing_wraps_redis_errors(self) -> None:
        async_redis = MagicMock()
        async_redis.delete = AsyncMock(side_effect=Exception("redis down"))
        store = RedisDedupeStore(MagicMock(), async_redis)

        with pytest.raises(RedisConnectionError, match="remover lock de dedupe"):
            await store.unmark_processing("msg-8")

    @pytest.mark.anyio
    async def test_seen_async_raises_without_async_client(self) -> None:
        store = RedisDedupeStore(MagicMock(), None)

        with pytest.raises(RuntimeError, match="Async Redis client"):
            await store.seen_async("msg-9", ttl=60)

    @pytest.mark.anyio
    async def test_seen_async_returns_false_for_new_key(self) -> None:
        async_redis = MagicMock()
        async_redis.set = AsyncMock(return_value=True)
        store = RedisDedupeStore(MagicMock(), async_redis)

        result = await store.seen_async("msg-9", ttl=60)

        assert result is False
        async_redis.set.assert_awaited_once_with("dedupe:msg-9", "1", nx=True, ex=60)

    @pytest.mark.anyio
    async def test_seen_async_returns_true_for_duplicate_key(self) -> None:
        async_redis = MagicMock()
        async_redis.set = AsyncMock(return_value=False)
        store = RedisDedupeStore(MagicMock(), async_redis)

        result = await store.seen_async("msg-10", ttl=60)

        assert result is True
        async_redis.set.assert_awaited_once_with("dedupe:msg-10", "1", nx=True, ex=60)
