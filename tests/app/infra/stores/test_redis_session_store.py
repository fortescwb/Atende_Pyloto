"""Testes do RedisSessionStore com mock."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infra.stores.redis_session_store import RedisSessionStore
from app.sessions.models import Session, SessionContext


class TestRedisSessionStore:
    """Testes do RedisSessionStore (API síncrona)."""

    def test_save_calls_setex(self) -> None:
        """Deve chamar setex com dados serializados."""
        mock_redis = MagicMock()
        store = RedisSessionStore(mock_redis)

        session = Session(
            session_id="redis-123",
            sender_id="sender-456",
            context=SessionContext(tenant_id="t1"),
        )

        # Chama sync save (não async)
        store.save(session, ttl_seconds=1800)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "session:redis-123"
        assert call_args[0][1] == 1800
        # Verifica que é JSON válido
        data = json.loads(call_args[0][2])
        assert data["session_id"] == "redis-123"

    def test_load_returns_session(self) -> None:
        """Deve carregar e deserializar sessão."""
        mock_redis = MagicMock()
        session_data = {
            "session_id": "load-123",
            "sender_id": "s",
            "current_state": "INITIAL",
            "context": {
                "tenant_id": "",
                "vertente": "geral",
                "rules": {},
                "limits": {},
            },
            "history": [],
            "turn_count": 0,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "expires_at": None,
        }
        mock_redis.get.return_value = json.dumps(session_data).encode()
        store = RedisSessionStore(mock_redis)

        loaded = store.load("load-123")

        assert loaded is not None
        assert loaded.session_id == "load-123"
        mock_redis.get.assert_called_once_with("session:load-123")

    def test_load_returns_none_for_missing(self) -> None:
        """Deve retornar None se chave não existe."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        store = RedisSessionStore(mock_redis)

        loaded = store.load("missing")
        assert loaded is None

    def test_delete_calls_redis_delete(self) -> None:
        """Deve chamar delete do Redis."""
        mock_redis = MagicMock()
        mock_redis.delete.return_value = 1
        store = RedisSessionStore(mock_redis)

        result = store.delete("del-123")

        assert result is True
        mock_redis.delete.assert_called_once_with("session:del-123")

    def test_exists_calls_redis_exists(self) -> None:
        """Deve chamar exists do Redis."""
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 1
        store = RedisSessionStore(mock_redis)

        result = store.exists("exists-123")

        assert result is True
        mock_redis.exists.assert_called_once_with("session:exists-123")


class TestRedisSessionStoreAsync:
    """Testes do RedisSessionStore (API assíncrona)."""

    @pytest.mark.anyio
    async def test_save_async_calls_setex(self) -> None:
        """Deve chamar setex assíncrono com dados serializados."""
        mock_sync_redis = MagicMock()
        mock_async_redis = AsyncMock()
        store = RedisSessionStore(mock_sync_redis, mock_async_redis)

        session = Session(
            session_id="async-save-123",
            sender_id="sender-456",
            context=SessionContext(tenant_id="t1"),
        )

        await store.save_async(session, ttl_seconds=1800)

        mock_async_redis.setex.assert_called_once()
        call_args = mock_async_redis.setex.call_args
        assert call_args[0][0] == "session:async-save-123"
        assert call_args[0][1] == 1800
        data = json.loads(call_args[0][2])
        assert data["session_id"] == "async-save-123"

    @pytest.mark.anyio
    async def test_load_async_returns_session(self) -> None:
        """Deve carregar e deserializar sessão (async)."""
        mock_sync_redis = MagicMock()
        mock_async_redis = AsyncMock()
        session_data = {
            "session_id": "async-load-123",
            "sender_id": "s",
            "current_state": "INITIAL",
            "context": {
                "tenant_id": "",
                "vertente": "geral",
                "rules": {},
                "limits": {},
            },
            "history": [],
            "turn_count": 0,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "expires_at": None,
        }
        mock_async_redis.get.return_value = json.dumps(session_data).encode()
        store = RedisSessionStore(mock_sync_redis, mock_async_redis)

        loaded = await store.load_async("async-load-123")

        assert loaded is not None
        assert loaded.session_id == "async-load-123"
        mock_async_redis.get.assert_called_once_with("session:async-load-123")

    @pytest.mark.anyio
    async def test_load_async_returns_none_for_missing(self) -> None:
        """Deve retornar None se chave não existe (async)."""
        mock_sync_redis = MagicMock()
        mock_async_redis = AsyncMock()
        mock_async_redis.get.return_value = None
        store = RedisSessionStore(mock_sync_redis, mock_async_redis)

        loaded = await store.load_async("missing")
        assert loaded is None

    @pytest.mark.anyio
    async def test_delete_async_calls_redis_delete(self) -> None:
        """Deve chamar delete assíncrono do Redis."""
        mock_sync_redis = MagicMock()
        mock_async_redis = AsyncMock()
        mock_async_redis.delete.return_value = 1
        store = RedisSessionStore(mock_sync_redis, mock_async_redis)

        result = await store.delete_async("async-del-123")

        assert result is True
        mock_async_redis.delete.assert_called_once_with("session:async-del-123")

    @pytest.mark.anyio
    async def test_exists_async_calls_redis_exists(self) -> None:
        """Deve chamar exists assíncrono do Redis."""
        mock_sync_redis = MagicMock()
        mock_async_redis = AsyncMock()
        mock_async_redis.exists.return_value = 1
        store = RedisSessionStore(mock_sync_redis, mock_async_redis)

        result = await store.exists_async("async-exists-123")

        assert result is True
        mock_async_redis.exists.assert_called_once_with("session:async-exists-123")

    @pytest.mark.anyio
    async def test_save_async_raises_without_async_client(self) -> None:
        """Deve lançar RuntimeError se async client não configurado."""
        mock_sync_redis = MagicMock()
        store = RedisSessionStore(mock_sync_redis, async_redis_client=None)

        session = Session(
            session_id="no-async",
            sender_id="s",
            context=SessionContext(tenant_id="t"),
        )

        with pytest.raises(RuntimeError, match="Async Redis client"):
            await store.save_async(session)
