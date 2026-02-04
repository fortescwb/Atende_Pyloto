"""Testes para ConversationStore protocol e FirestoreConversationStore."""

from __future__ import annotations

from datetime import UTC, datetime

from app.protocols.conversation_store import (
    ConversationMessage,
    ConversationStoreError,
    LeadData,
)


class TestConversationMessage:
    """Testes para o dataclass ConversationMessage."""

    def test_create_user_message(self) -> None:
        """Cria mensagem de usuário."""
        msg = ConversationMessage(
            message_id="msg_123",
            role="user",
            content="Olá, tudo bem?",
            timestamp=datetime.now(UTC),
            channel="whatsapp",
        )
        assert msg.role == "user"
        assert msg.content == "Olá, tudo bem?"
        assert msg.channel == "whatsapp"

    def test_create_assistant_message(self) -> None:
        """Cria mensagem de assistente."""
        msg = ConversationMessage(
            message_id="msg_456",
            role="assistant",
            content="Tudo bem sim! Como posso ajudar?",
            timestamp=datetime.now(UTC),
            detected_intent="saudacao",
        )
        assert msg.role == "assistant"
        assert msg.detected_intent == "saudacao"

    def test_message_immutable(self) -> None:
        """Mensagem é imutável (frozen)."""
        msg = ConversationMessage(
            message_id="msg_789",
            role="user",
            content="teste",
            timestamp=datetime.now(UTC),
        )
        # frozen=True impede alteração
        try:
            msg.content = "outro"  # type: ignore[misc]
            raise AssertionError("Deveria lançar FrozenInstanceError")
        except AttributeError:
            pass  # Esperado


class TestLeadData:
    """Testes para o dataclass LeadData."""

    def test_create_lead_minimal(self) -> None:
        """Cria lead com dados mínimos."""
        lead = LeadData(phone_hash="abc123")
        assert lead.phone_hash == "abc123"
        assert lead.name == ""
        assert lead.tenant_id == "default"

    def test_create_lead_full(self) -> None:
        """Cria lead com todos os dados."""
        now = datetime.now(UTC)
        lead = LeadData(
            phone_hash="def456",
            name="João Silva",
            email="joao@email.com",
            first_contact=now,
            last_contact=now,
            primary_intent="orcamento",
            total_messages=5,
            tenant_id="empresa_x",
            channel="whatsapp",
            metadata={"source": "campanha_1"},
        )
        assert lead.name == "João Silva"
        assert lead.email == "joao@email.com"
        assert lead.total_messages == 5
        assert lead.metadata == {"source": "campanha_1"}

    def test_lead_immutable(self) -> None:
        """Lead é imutável (frozen)."""
        lead = LeadData(phone_hash="xyz")
        try:
            lead.name = "Outro"  # type: ignore[misc]
            raise AssertionError("Deveria lançar FrozenInstanceError")
        except AttributeError:
            pass  # Esperado


class TestConversationStoreError:
    """Testes para a exceção ConversationStoreError."""

    def test_error_message(self) -> None:
        """Erro tem mensagem correta."""
        error = ConversationStoreError("Falha ao persistir")
        assert str(error) == "Falha ao persistir"

    def test_error_is_exception(self) -> None:
        """Erro herda de Exception."""
        error = ConversationStoreError("teste")
        assert isinstance(error, Exception)
