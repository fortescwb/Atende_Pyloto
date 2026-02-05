import pytest

from ai.models.otto import OttoDecision
from app.protocols.models import NormalizedMessage
from app.sessions.models import Session, SessionContext
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
                text="hi",
            )
        ]


class DummyDedupe:
    async def is_duplicate(self, message_id: str) -> bool:
        return False

    async def mark_processed(self, message_id: str) -> None:
        return None


class DummySender:
    async def send(self, request, payload):
        return type("Resp", (), {"success": True})()


@pytest.mark.asyncio
async def test_process_inbound_uses_injected_protocols():
    otto = FakeOttoAgent()
    session_mgr = FakeSessionManager()

    usecase = ProcessInboundCanonicalUseCase(
        normalizer=DummyNormalizer(),
        session_manager=session_mgr,
        dedupe=DummyDedupe(),
        otto_agent=otto,
        outbound_sender=DummySender(),
    )

    res = await usecase.execute(payload={"some": "payload"}, correlation_id="c1", tenant_id="t1")
    assert otto.called is True
    assert session_mgr.saved is True
    assert res.processed >= 0
