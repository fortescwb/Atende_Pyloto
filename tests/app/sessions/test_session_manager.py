"""Testes para SessionManager com dual-write.

Testa:
    - Criação de sessão
    - Recuperação de sessão do Redis
    - Dual-write (Redis + Firestore)
    - Recovery de histórico do Firestore
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.protocols.conversation_store import ConversationMessage, LeadData
from app.sessions.manager import SessionManager
from app.sessions.models import HistoryRole

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_session_store() -> AsyncMock:
    """Store de sessão mock."""
    store = AsyncMock()
    store.load_async = AsyncMock(return_value=None)
    store.save_async = AsyncMock()
    store.delete_async = AsyncMock()
    return store


@pytest.fixture
def mock_conversation_store() -> AsyncMock:
    """Store de conversas mock."""
    store = AsyncMock()
    store.get_lead = AsyncMock(return_value=None)
    store.get_messages = AsyncMock(return_value=[])
    store.append_message = AsyncMock()
    store.upsert_lead = AsyncMock()
    return store


@pytest.fixture
def manager(mock_session_store: AsyncMock) -> SessionManager:
    """SessionManager sem ConversationStore."""
    return SessionManager(store=mock_session_store)


@pytest.fixture
def manager_with_firestore(
    mock_session_store: AsyncMock,
    mock_conversation_store: AsyncMock,
) -> SessionManager:
    """SessionManager com ConversationStore."""
    return SessionManager(
        store=mock_session_store,
        conversation_store=mock_conversation_store,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Testes: Criação de Sessão
# ──────────────────────────────────────────────────────────────────────────────


class TestSessionCreation:
    """Testes de criação de sessão."""

    @pytest.mark.asyncio
    async def test_create_new_session(
        self,
        manager: SessionManager,
        mock_session_store: AsyncMock,
    ) -> None:
        """Cria nova sessão quando não existe no Redis."""
        session = await manager.resolve_or_create(
            sender_id="5511999998888",
            tenant_id="tenant-123",
            vertente="vendas",
            whatsapp_name="Joao",
        )

        assert session.session_id.startswith("sess_")
        assert session.context.tenant_id == "tenant-123"
        assert session.context.vertente == "vendas"
        mock_session_store.save_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_existing_session(
        self,
        manager: SessionManager,
        mock_session_store: AsyncMock,
    ) -> None:
        """Retorna sessão existente do Redis."""
        from datetime import timedelta

        existing_data = {
            "session_id": "sess_existing_123",
            "sender_id": "hash123",
            "current_state": "TRIAGE",
            "context": {"tenant_id": "tenant-123", "vertente": "vendas"},
            "history": [],
            "contact_card": {},
            "turn_count": 3,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        }
        mock_session_store.load_async.return_value = existing_data

        session = await manager.resolve_or_create(sender_id="5511999998888")

        assert session.session_id == "sess_existing_123"
        assert session.turn_count == 3


# ──────────────────────────────────────────────────────────────────────────────
# Testes: Dual-write
# ──────────────────────────────────────────────────────────────────────────────


class TestDualWrite:
    """Testes de dual-write (Redis + Firestore)."""

    @pytest.mark.asyncio
    async def test_add_message_saves_to_redis(
        self,
        manager_with_firestore: SessionManager,
        mock_session_store: AsyncMock,
    ) -> None:
        """add_message salva no Redis."""
        session = await manager_with_firestore.resolve_or_create(
            sender_id="5511999998888",
            tenant_id="tenant-123",
        )
        mock_session_store.save_async.reset_mock()

        await manager_with_firestore.add_message(
            session=session,
            content="Olá, quero saber sobre sistemas",
            role=HistoryRole.USER,
        )

        # Redis deve ser chamado
        mock_session_store.save_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_message_fires_firestore_task(
        self,
        manager_with_firestore: SessionManager,
        mock_conversation_store: AsyncMock,
    ) -> None:
        """add_message dispara task para Firestore (fire-and-forget)."""
        import asyncio

        session = await manager_with_firestore.resolve_or_create(
            sender_id="5511999998888",
            tenant_id="tenant-123",
        )

        await manager_with_firestore.add_message(
            session=session,
            content="Olá, quero saber sobre sistemas",
            role=HistoryRole.USER,
            detected_intent="PRICING_INQUIRY",
        )

        # Aguarda tasks pendentes
        await asyncio.sleep(0.1)

        # Firestore deve ser chamado
        mock_conversation_store.append_message.assert_called_once()
        call_kwargs = mock_conversation_store.append_message.call_args
        assert call_kwargs.kwargs["tenant_id"] == "tenant-123"

    @pytest.mark.asyncio
    async def test_add_message_without_firestore_works(
        self,
        manager: SessionManager,
        mock_session_store: AsyncMock,
    ) -> None:
        """add_message funciona sem ConversationStore configurado."""
        session = await manager.resolve_or_create(sender_id="5511999998888")
        mock_session_store.save_async.reset_mock()

        await manager.add_message(
            session=session,
            content="Olá!",
            role=HistoryRole.USER,
        )

        # Redis deve ser chamado, sem erro
        mock_session_store.save_async.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# Testes: Recovery do Firestore
# ──────────────────────────────────────────────────────────────────────────────


class TestFirestoreRecovery:
    """Testes de recuperação de histórico do Firestore."""

    @pytest.mark.asyncio
    async def test_recovery_loads_contact_card(
        self,
        manager_with_firestore: SessionManager,
        mock_conversation_store: AsyncMock,
    ) -> None:
        """Recupera contato do Firestore."""
        mock_conversation_store.get_lead.return_value = LeadData(
            phone_hash="hash123",
            name="Maria",
            email="maria@example.com",
            primary_intent="sob_medida",
            tenant_id="tenant-123",
        )

        session = await manager_with_firestore.resolve_or_create(
            sender_id="5511999998888",
            tenant_id="tenant-123",
            whatsapp_name="Maria",
        )

        assert session.contact_card is not None
        assert session.contact_card.full_name == "Maria"
        assert session.contact_card.email == "maria@example.com"
        assert session.contact_card.primary_interest == "sob_medida"

    @pytest.mark.asyncio
    async def test_recovery_loads_message_history(
        self,
        manager_with_firestore: SessionManager,
        mock_conversation_store: AsyncMock,
    ) -> None:
        """Recupera histórico de mensagens do Firestore."""
        mock_conversation_store.get_messages.return_value = [
            ConversationMessage(
                message_id="msg_001",
                role="user",
                content="Oi, quero um sistema",
                timestamp=datetime.now(UTC),
                channel="whatsapp",
            ),
            ConversationMessage(
                message_id="msg_002",
                role="assistant",
                content="Olá! Como posso ajudar?",
                timestamp=datetime.now(UTC),
                channel="whatsapp",
            ),
        ]

        session = await manager_with_firestore.resolve_or_create(
            sender_id="5511999998888",
            tenant_id="tenant-123",
            whatsapp_name="Maria",
        )

        assert len(session.history) == 2
        assert session.history[0].role == HistoryRole.USER
        assert session.history[1].role == HistoryRole.ASSISTANT

    @pytest.mark.asyncio
    async def test_recovery_handles_firestore_error(
        self,
        manager_with_firestore: SessionManager,
        mock_conversation_store: AsyncMock,
    ) -> None:
        """Sessão é criada mesmo se Firestore falhar."""
        mock_conversation_store.get_lead.side_effect = Exception("Firestore error")

        # Não deve lançar exceção
        session = await manager_with_firestore.resolve_or_create(
            sender_id="5511999998888",
        )

        assert session.session_id.startswith("sess_")
        assert session.contact_card is None  # Fallback vazio

    @pytest.mark.asyncio
    async def test_no_recovery_without_firestore(
        self,
        manager: SessionManager,
    ) -> None:
        """Sem ConversationStore, não tenta recuperar."""
        session = await manager.resolve_or_create(sender_id="5511999998888")

        assert session.history == []
        assert session.contact_card is None


# ──────────────────────────────────────────────────────────────────────────────
# Testes: Update Lead Profile
# ──────────────────────────────────────────────────────────────────────────────


class TestUpdateContactCard:
    """Testes de atualizacao do contato."""

    @pytest.mark.asyncio
    async def test_update_contact_card(
        self,
        manager_with_firestore: SessionManager,
        mock_session_store: AsyncMock,
        mock_conversation_store: AsyncMock,
    ) -> None:
        """Atualiza contato e persiste no Firestore."""
        import asyncio

        session = await manager_with_firestore.resolve_or_create(
            sender_id="5511999998888",
            tenant_id="tenant-123",
            whatsapp_name="Maria",
        )

        await manager_with_firestore.update_contact_card(
            session,
            full_name="Maria",
            email="maria@example.com",
            primary_interest="sob_medida",
        )

        # Aguarda tasks pendentes
        await asyncio.sleep(0.1)

        assert session.contact_card is not None
        assert session.contact_card.full_name == "Maria"
        assert session.contact_card.email == "maria@example.com"
        mock_conversation_store.upsert_lead.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# Testes: Close Session
# ──────────────────────────────────────────────────────────────────────────────


class TestCloseSession:
    """Testes de encerramento de sessão."""

    @pytest.mark.asyncio
    async def test_close_session(
        self,
        manager: SessionManager,
        mock_session_store: AsyncMock,
    ) -> None:
        """Encerra sessão e remove do Redis."""
        session = await manager.resolve_or_create(sender_id="5511999998888")

        await manager.close(session, reason="completed")

        mock_session_store.delete_async.assert_called_once()
