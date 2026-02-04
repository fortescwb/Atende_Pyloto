import pytest

from app.protocols.master_decider import MasterDecision
from app.protocols.session_manager import Session
from app.use_cases.whatsapp.process_inbound_canonical import ProcessInboundCanonicalUseCase


class FakeMasterDecider:
    def __init__(self):
        self.called = False

    def decide(self, *, session, ai_result, fsm_result, user_input: str) -> MasterDecision:
        self.called = True
        return MasterDecision(final_state="S", should_close_session=False)


class FakeSessionManager:
    def __init__(self):
        self.saved = False

    async def resolve_or_create(self, *, sender_id: str, tenant_id: str) -> Session:
        s = Session(
            session_id="s1",
            current_state=type("S", (), {"name": "INITIAL"})(),
            history=[],
            context=type("C", (), {"tenant_id": "t", "vertente": None})(),
            turn_count=0,
        )
        # atributos/metodos esperados pelo UseCase + MasterDecider
        s.is_terminal = False

        def add_to_history(text: str) -> None:
            s.history.append(text)

        def transition_to(state_name: str) -> None:
            s.current_state = type("S", (), {"name": state_name})()

        s.add_to_history = add_to_history
        s.transition_to = transition_to

        return s


    async def save(self, session: Session) -> None:
        self.saved = True

    async def close(self, session: Session, reason: str) -> None:
        pass


class DummyNormalizer:
    def normalize(self, payload):
        # one normalized message minimal
        return [type("M", (), {"from_number": "+123", "text": "hi", "message_id": "mid", "from": "", "to": ""})()]


class DummyDedupe:
    async def is_duplicate(self, message_id: str) -> bool:
        return False

    async def mark_processed(self, message_id: str) -> None:
        return None


class DummyAI:
    async def process_message(self, **kwargs):
        suggested = type("S", (), {"state": "TRIAGE", "confidence": 0.9})()
        state_sugg = type("StateRes", (), {"suggested_next_states": [suggested]})()

        Decision = type("Dec", (), {"final_text": "ok", "understood": True, "final_state": "TRIAGE", "final_message_type": "text", "should_escalate": False})()
        ResponseGen = type("RGen", (), {"requires_human_review": False})()

        return type(
            "R",
            (),
            {
                "state_suggestion": state_sugg,
                "understood": True,
                "overall_confidence": 0.9,
                "final_decision": Decision,
                "should_escalate": False,
                "response_generation": ResponseGen,
            },
        )()


class DummySender:
    async def send(self, request, payload):
        return type("Resp", (), {"success": True})()


@pytest.mark.asyncio
async def test_process_inbound_uses_injected_protocols():
    master = FakeMasterDecider()
    session_mgr = FakeSessionManager()

    # Inject master_decider (preferred) and session_manager protocol
    usecase = ProcessInboundCanonicalUseCase(
        normalizer=DummyNormalizer(),
        session_manager=session_mgr,
        dedupe=DummyDedupe(),
        ai_orchestrator=DummyAI(),
        outbound_sender=DummySender(),
        master_decider=master,
    )

    res = await usecase.execute(payload={"some": "payload"}, correlation_id="c1", tenant_id="t1")
    assert master.called is True
    assert res.processed >= 0
