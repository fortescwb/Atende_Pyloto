"""Testes para o decisor mestre."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.master_decider import MasterDecider, MasterDecision
from app.sessions.models import Session, SessionContext
from fsm.states import SessionState

# ========== MOCKS para estrutura de 4 agentes LLM ==========


@dataclass
class MockStateSuggestion:
    """Mock de sugestão de estado para StateAgent (LLM #1)."""

    state: str = "TRIAGE"
    confidence: float = 0.85
    rationale: str = "Mock suggestion"


@dataclass
class MockStateAgentResult:
    """Mock de resultado do StateAgent (LLM #1)."""

    current_state: str = "INITIAL"
    suggested_next_states: list[MockStateSuggestion] = field(
        default_factory=lambda: [MockStateSuggestion()]
    )
    confidence: float = 0.85
    understood: bool = True
    rationale: str = "Mock state result"


@dataclass
class MockResponseGeneration:
    """Mock de resultado do ResponseAgent (LLM #2)."""

    text_content: str = "Olá! Como posso ajudar?"
    options: tuple = ()
    requires_human_review: bool = False
    confidence: float = 0.85


@dataclass
class MockMessageTypeSelection:
    """Mock de resultado do MessageTypeAgent (LLM #3)."""

    message_type: str = "text"
    confidence: float = 0.9


@dataclass
class MockDecisionAgentResult:
    """Mock de resultado do DecisionAgent (LLM #4)."""

    final_state: str = "TRIAGE"
    final_text: str = "Olá! Como posso ajudar?"
    final_message_type: str = "text"
    understood: bool = True
    confidence: float = 0.85
    should_escalate: bool = False
    rationale: str = "Mock decision"


@dataclass
class MockOrchestratorResult:
    """Mock de resultado do orquestrador com estrutura de 4 agentes."""

    state_suggestion: MockStateAgentResult
    response_generation: MockResponseGeneration
    message_type_selection: MockMessageTypeSelection
    final_decision: MockDecisionAgentResult
    overall_confidence: float = 0.88
    understood: bool = True
    should_escalate: bool = False


@dataclass
class MockTransition:
    """Mock de transição."""
    to_state: SessionState = SessionState.TRIAGE


@dataclass
class MockTransitionResult:
    """Mock de resultado de transição."""
    success: bool = True
    transition: MockTransition | None = None


def create_mock_session() -> Session:
    """Cria uma sessão mock para testes."""
    return Session(
        session_id="sess-test-123",
        sender_id="hash-sender",
        current_state=SessionState.INITIAL,
        context=SessionContext(tenant_id="tenant-1"),
        turn_count=5,
    )


def create_mock_ai_result() -> MockOrchestratorResult:
    """Cria um resultado de AI mock com estrutura de 4 agentes."""
    return MockOrchestratorResult(
        state_suggestion=MockStateAgentResult(),
        response_generation=MockResponseGeneration(),
        message_type_selection=MockMessageTypeSelection(),
        final_decision=MockDecisionAgentResult(),
    )


class TestMasterDecider:
    """Testes para o decisor mestre."""

    def test_decide_normal_flow(self) -> None:
        """Verifica decisão em fluxo normal."""
        decider = MasterDecider()

        session = create_mock_session()
        ai_result = create_mock_ai_result()
        fsm_result = MockTransitionResult(
            success=True,
            transition=MockTransition(to_state=SessionState.TRIAGE),
        )

        decision = decider.decide(
            session=session,
            ai_result=ai_result,
            fsm_result=fsm_result,
            user_input="Olá, bom dia!",
        )

        assert isinstance(decision, MasterDecision)
        assert "Olá" in decision.final_text
        assert decision.final_message_type == "text"
        assert decision.should_close_session is False
        assert decision.requires_human_escalation is False

    def test_decide_force_close(self) -> None:
        """Verifica encerramento forçado por keyword."""
        decider = MasterDecider()

        session = create_mock_session()
        ai_result = create_mock_ai_result()
        fsm_result = MockTransitionResult(success=True, transition=MockTransition())

        decision = decider.decide(
            session=session,
            ai_result=ai_result,
            fsm_result=fsm_result,
            user_input="Quero encerrar o atendimento",
        )

        assert decision.should_close_session is True
        assert decision.close_reason == "user_request"
        assert "Encerrando" in decision.final_text

    def test_decide_force_escalation(self) -> None:
        """Verifica escalação forçada por keyword."""
        decider = MasterDecider()

        session = create_mock_session()
        ai_result = create_mock_ai_result()
        fsm_result = MockTransitionResult(success=True, transition=MockTransition())

        decision = decider.decide(
            session=session,
            ai_result=ai_result,
            fsm_result=fsm_result,
            user_input="Preciso falar com um atendente humano",
        )

        assert decision.requires_human_escalation is True
        assert "atendente humano" in decision.final_text

    def test_decide_turns_exceeded_hint(self) -> None:
        """Verifica hint quando turnos excedem limite."""
        decider = MasterDecider()

        session = Session(
            session_id="sess-long",
            sender_id="hash-sender",
            current_state=SessionState.COLLECTING_INFO,
            turn_count=25,  # Acima do limite
        )
        ai_result = create_mock_ai_result()
        fsm_result = MockTransitionResult(success=True, transition=MockTransition())

        decision = decider.decide(
            session=session,
            ai_result=ai_result,
            fsm_result=fsm_result,
            user_input="Mais uma pergunta",
        )

        assert "conversa está longa" in decision.final_text

    def test_decide_audit_record(self) -> None:
        """Verifica que registro de auditoria é criado com estrutura de 4 agentes."""
        decider = MasterDecider()

        session = create_mock_session()
        ai_result = create_mock_ai_result()
        fsm_result = MockTransitionResult(success=True, transition=MockTransition())

        decision = decider.decide(
            session=session,
            ai_result=ai_result,
            fsm_result=fsm_result,
            user_input="Olá",
        )

        audit = decision.audit_record
        assert "timestamp" in audit
        assert audit["session_id"] == "sess-test-123"
        # StateAgent (LLM #1)
        assert audit["state_suggested"] == "TRIAGE"
        assert "state_confidence" in audit
        # ResponseAgent (LLM #2)
        assert "response_confidence" in audit
        # MessageTypeAgent (LLM #3)
        assert audit["message_type"] == "text"
        assert "message_type_confidence" in audit
        # DecisionAgent (LLM #4)
        assert audit["final_state"] == "TRIAGE"
        assert "overall_confidence" in audit

    def test_decide_fsm_failure_reduces_confidence(self) -> None:
        """Verifica que falha na FSM reduz confiança."""
        decider = MasterDecider()

        session = create_mock_session()
        ai_result = create_mock_ai_result()
        fsm_result = MockTransitionResult(success=False, transition=None)

        decision = decider.decide(
            session=session,
            ai_result=ai_result,
            fsm_result=fsm_result,
            user_input="Olá",
        )

        # Quando FSM falha, confiança é limitada a 0.5
        assert decision.confidence <= 0.5

    def test_decide_force_close_100_percent_confidence(self) -> None:
        """Verifica que regras duras têm 100% de confiança."""
        decider = MasterDecider()

        session = create_mock_session()
        ai_result = create_mock_ai_result()
        fsm_result = MockTransitionResult(success=True, transition=MockTransition())

        decision = decider.decide(
            session=session,
            ai_result=ai_result,
            fsm_result=fsm_result,
            user_input="encerrar",
        )

        assert decision.confidence == 1.0


class TestMasterDecision:
    """Testes para o dataclass MasterDecision."""

    def test_decision_defaults(self) -> None:
        """Verifica valores padrão."""
        decision = MasterDecision(
            final_text="Olá",
            final_message_type="text",
            final_state="INITIAL",
        )

        assert decision.should_close_session is False
        assert decision.close_reason is None
        assert decision.requires_human_escalation is False
        assert decision.confidence == 0.8
