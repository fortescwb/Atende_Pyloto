"""Testes do RedisDedupeStore com mock."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.infra.stores.redis_dedupe_store import RedisDedupeStore


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
