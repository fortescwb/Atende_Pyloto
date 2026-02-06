"""Testes para o modelo de sessão."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from app.domain.contact_card import ContactCard
from app.sessions.models import HistoryRole, Session, SessionContext
from fsm.states import SessionState


class TestSessionContext:
    """Testes para SessionContext."""

    def test_default_values(self) -> None:
        """Verifica valores padrão do contexto."""
        ctx = SessionContext()
        assert ctx.tenant_id == ""
        assert ctx.vertente == "geral"
        assert ctx.rules == {}
        assert ctx.limits == {}
        assert ctx.prompt_vertical == ""
        assert ctx.prompt_contexts == []

    def test_custom_values(self) -> None:
        """Verifica valores customizados."""
        ctx = SessionContext(
            tenant_id="tenant-123",
            vertente="vendas",
            rules={"max_options": 3},
            limits={"timeout": 3600},
            prompt_vertical="automacao",
            prompt_contexts=["vertentes/automacao/objections.yaml"],
        )
        assert ctx.tenant_id == "tenant-123"
        assert ctx.vertente == "vendas"


class TestSession:
    """Testes para Session."""

    def test_create_session(self) -> None:
        """Verifica criação de sessão."""
        session = Session(
            session_id="sess-123",
            sender_id="sender-hash",
        )
        assert session.session_id == "sess-123"
        assert session.current_state == SessionState.INITIAL
        assert session.turn_count == 0

    def test_is_expired_false(self) -> None:
        """Verifica que sessão não expirada retorna False."""
        session = Session(
            session_id="sess-123",
            sender_id="sender-hash",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert session.is_expired is False

    def test_is_expired_true(self) -> None:
        """Verifica que sessão expirada retorna True."""
        session = Session(
            session_id="sess-123",
            sender_id="sender-hash",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        assert session.is_expired is True

    def test_is_expired_none(self) -> None:
        """Verifica que sessão sem expiração não está expirada."""
        session = Session(
            session_id="sess-123",
            sender_id="sender-hash",
            expires_at=None,
        )
        assert session.is_expired is False

    def test_is_terminal(self) -> None:
        """Verifica detecção de estado terminal."""
        session = Session(
            session_id="sess-123",
            sender_id="sender-hash",
            current_state=SessionState.HANDOFF_HUMAN,
        )
        assert session.is_terminal is True

    def test_is_not_terminal(self) -> None:
        """Verifica detecção de estado não-terminal."""
        session = Session(
            session_id="sess-123",
            sender_id="sender-hash",
            current_state=SessionState.TRIAGE,
        )
        assert session.is_terminal is False

    def test_add_to_history(self) -> None:
        """Verifica adição ao histórico."""
        session = Session(
            session_id="sess-123",
            sender_id="sender-hash",
        )
        session.add_to_history("Mensagem 1")
        session.add_to_history("Mensagem 2")

        assert len(session.history) == 2
        assert session.history[0].content == "Mensagem 1"
        assert session.history[0].role == HistoryRole.USER

    def test_add_to_history_limit(self) -> None:
        """Verifica limite do histórico (FIFO)."""
        session = Session(
            session_id="sess-123",
            sender_id="sender-hash",
        )

        for i in range(15):
            session.add_to_history(f"Mensagem {i}")

        assert len(session.history) == 10
        assert session.history[0].content == "Mensagem 5"  # Primeiras 5 foram removidas

    def test_transition_to(self) -> None:
        """Verifica transição de estado."""
        session = Session(
            session_id="sess-123",
            sender_id="sender-hash",
        )

        session.transition_to(SessionState.TRIAGE)

        assert session.current_state == SessionState.TRIAGE
        assert session.turn_count == 1

    def test_to_dict(self) -> None:
        """Verifica serialização para dict."""
        session = Session(
            session_id="sess-123",
            sender_id="sender-hash",
            current_state=SessionState.TRIAGE,
        )

        data = session.to_dict()

        assert data["session_id"] == "sess-123"
        assert data["current_state"] == "TRIAGE"
        assert "created_at" in data

    def test_to_dict_json_serializable_with_contact_card(self) -> None:
        """to_dict deve ser serializável em JSON mesmo com ContactCard."""
        contact_card = ContactCard(
            wa_id="5511999998888",
            phone="5511999998888",
            whatsapp_name="Joao",
        )
        session = Session(
            session_id="sess-cc",
            sender_id="sender-hash",
            current_state=SessionState.TRIAGE,
            contact_card=contact_card,
        )

        data = session.to_dict()

        # Não pode levantar TypeError por datetime não-serializável.
        json.dumps(data)
        assert isinstance(data["contact_card"]["first_contact_at"], str)

    def test_from_dict(self) -> None:
        """Verifica deserialização de dict."""
        data = {
            "session_id": "sess-123",
            "sender_id": "sender-hash",
            "current_state": "TRIAGE",
            "context": {
                "tenant_id": "tenant-1",
                "vertente": "suporte",
            },
            "history": ["msg1", "msg2"],
            "turn_count": 5,
            "created_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "2025-01-01T01:00:00+00:00",
        }

        session = Session.from_dict(data)

        assert session.session_id == "sess-123"
        assert session.current_state == SessionState.TRIAGE
        assert session.context.tenant_id == "tenant-1"
        assert len(session.history) == 2
        assert session.turn_count == 5

    def test_roundtrip_serialization(self) -> None:
        """Verifica que serialização e deserialização são inversas."""
        original = Session(
            session_id="sess-test",
            sender_id="hash-test",
            current_state=SessionState.COLLECTING_INFO,
            context=SessionContext(tenant_id="t1", vertente="vendas"),
            turn_count=3,
        )
        # Adiciona histórico usando o método correto
        original.add_to_history("a")
        original.add_to_history("b")
        original.add_to_history("c")

        data = original.to_dict()
        restored = Session.from_dict(data)

        assert restored.session_id == original.session_id
        assert restored.current_state == original.current_state
        assert restored.context.tenant_id == original.context.tenant_id
        assert len(restored.history) == len(original.history)
        assert restored.history[0].content == original.history[0].content
        assert restored.turn_count == original.turn_count
