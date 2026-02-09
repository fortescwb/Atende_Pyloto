"""Testes do fast-path de respostas fixas no inbound WhatsApp."""

from __future__ import annotations

import pytest

from ai.models.otto import OttoDecision
from app.protocols.models import NormalizedMessage
from app.sessions.models import HistoryRole, Session, SessionContext
from app.use_cases.whatsapp.process_inbound_canonical import ProcessInboundCanonicalUseCase
from fsm.states import SessionState


class FakeOttoAgent:
    def __init__(self) -> None:
        self.called = False

    async def decide(self, request):
        self.called = True
        return OttoDecision(
            next_state="TRIAGE",
            response_text="ok",
            message_type="text",
            confidence=0.9,
            requires_human=False,
        )


class FakeSessionManager:
    def __init__(self) -> None:
        self.saved = False
        self.session = Session(
            session_id="s1",
            sender_id="hash",
            current_state=SessionState.INITIAL,
            context=SessionContext(tenant_id="t", vertente="geral"),
            history=[],
            turn_count=0,
        )

    async def resolve_or_create(
        self,
        *,
        sender_id: str,
        tenant_id: str,
        whatsapp_name: str | None = None,
    ) -> Session:
        return self.session

    async def save(self, session: Session) -> None:
        self.saved = True

    async def close(self, session: Session, reason: str) -> None:
        return None


class DummyNormalizer:
    def normalize(self, payload):
        return [
            NormalizedMessage(
                message_id="mid",
                from_number="+123",
                message_type="text",
                text="/automacao",
            )
        ]


class DummyDedupe:
    async def is_duplicate(self, message_id: str) -> bool:
        return False

    async def mark_processing(self, message_id: str, ttl: int = 30) -> None:
        return None

    async def mark_processed(self, message_id: str) -> None:
        return None

    async def unmark_processing(self, message_id: str) -> None:
        return None


class DummySender:
    async def send(self, request, payload):
        return type("Resp", (), {"success": True})()


@pytest.mark.asyncio
async def test_fixed_reply_bypasses_agents_and_updates_history() -> None:
    otto = FakeOttoAgent()
    session_mgr = FakeSessionManager()

    usecase = ProcessInboundCanonicalUseCase(
        normalizer=DummyNormalizer(),
        session_manager=session_mgr,
        dedupe=DummyDedupe(),
        otto_agent=otto,
        outbound_sender=DummySender(),
    )

    result = await usecase.execute(payload={"some": "payload"}, correlation_id="c1", tenant_id="t1")

    assert otto.called is False
    assert session_mgr.saved is True
    assert result.sent == 1
    assert len(session_mgr.session.history) == 2
    assert session_mgr.session.history[0].role == HistoryRole.USER
    assert session_mgr.session.history[1].role == HistoryRole.ASSISTANT
    assert "Otto, assistente virtual da Pyloto" in session_mgr.session.history[1].content
    assert session_mgr.session.context.prompt_vertical == "automacao_atendimento"
