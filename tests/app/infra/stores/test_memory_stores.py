"""Testes dos stores em memória."""

from __future__ import annotations

import pytest

from app.infra.stores.memory_stores import (
    MemoryAuditStore,
    MemoryDedupeStore,
    MemorySessionStore,
)
from app.sessions.models import Session, SessionContext


class TestMemorySessionStore:
    """Testes do MemorySessionStore."""

    def test_save_and_load_session(self) -> None:
        """Deve salvar e carregar sessão."""
        store = MemorySessionStore()
        session = Session(
            session_id="test-123",
            sender_id="sender-456",
            context=SessionContext(tenant_id="tenant-1"),
        )

        store.save(session, ttl_seconds=3600)
        loaded = store.load("test-123")

        assert loaded is not None
        assert loaded.session_id == "test-123"
        assert loaded.sender_id == "sender-456"
        assert loaded.context.tenant_id == "tenant-1"

    def test_load_nonexistent_returns_none(self) -> None:
        """Deve retornar None para sessão inexistente."""
        store = MemorySessionStore()
        loaded = store.load("nonexistent")
        assert loaded is None

    def test_exists_returns_true_for_existing(self) -> None:
        """Deve retornar True se sessão existe."""
        store = MemorySessionStore()
        session = Session(session_id="exists-123", sender_id="s")
        store.save(session)

        assert store.exists("exists-123") is True
        assert store.exists("not-exists") is False

    def test_delete_removes_session(self) -> None:
        """Deve remover sessão."""
        store = MemorySessionStore()
        session = Session(session_id="del-123", sender_id="s")
        store.save(session)

        assert store.delete("del-123") is True
        assert store.exists("del-123") is False
        assert store.delete("del-123") is False  # Já deletado


class TestMemoryDedupeStore:
    """Testes do MemoryDedupeStore."""

    def test_seen_returns_false_for_new_key(self) -> None:
        """Deve retornar False para chave nova."""
        store = MemoryDedupeStore()
        result = store.seen("new-key", ttl=3600)
        assert result is False

    def test_seen_returns_true_for_duplicate(self) -> None:
        """Deve retornar True para chave duplicada."""
        store = MemoryDedupeStore()
        store.seen("dup-key", ttl=3600)
        result = store.seen("dup-key", ttl=3600)
        assert result is True

    @pytest.mark.anyio
    async def test_is_duplicate_async(self) -> None:
        """Teste async de is_duplicate."""
        store = MemoryDedupeStore()
        await store.mark_processed("async-key", ttl=3600)
        is_dup = await store.is_duplicate("async-key")
        assert is_dup is True

    @pytest.mark.anyio
    async def test_mark_processed_async(self) -> None:
        """Teste async de mark_processed."""
        store = MemoryDedupeStore()
        is_dup_before = await store.is_duplicate("mark-key")
        assert is_dup_before is False

        await store.mark_processed("mark-key", ttl=3600)
        is_dup_after = await store.is_duplicate("mark-key")
        assert is_dup_after is True


class TestMemoryAuditStore:
    """Testes do MemoryAuditStore."""

    def test_append_adds_record(self) -> None:
        """Deve adicionar registro."""
        store = MemoryAuditStore()
        store.append({"event_type": "decision", "session_id": "s1"})
        store.append({"event_type": "transition", "session_id": "s2"})

        records = store.get_records()
        assert len(records) == 2
        assert records[0]["event_type"] == "decision"
        assert records[1]["session_id"] == "s2"

    def test_respects_max_records(self) -> None:
        """Deve respeitar limite máximo de registros."""
        store = MemoryAuditStore(max_records=3)
        for i in range(5):
            store.append({"index": i})

        records = store.get_records()
        assert len(records) == 3
        # Mantém os últimos 3
        assert records[0]["index"] == 2
        assert records[2]["index"] == 4
