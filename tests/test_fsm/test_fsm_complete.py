"""
Testes abrangentes para o módulo FSM.

Seguindo REGRAS_E_PADROES.md § 8.1:
- Testamos comportamento e contrato público
- Um teste cobre múltiplos componentes relacionados
- Foco em cenários válidos + inválidos + bordas
"""

from datetime import datetime

import pytest

# Imports do módulo fsm - testa todos os exports públicos
from fsm import (
    DEFAULT_INITIAL_STATE,
    INITIAL_STATES,
    TERMINAL_STATES,
    # Transições
    VALID_TRANSITIONS,
    # Manager
    FSMStateMachine,
    # Guards
    GuardResult,
    # Estados
    SessionState,
    # Types
    StateTransition,
    TransitionResult,
    create_fsm,
    evaluate_guards,
    get_valid_targets,
    is_terminal,
    is_transition_valid,
    is_valid_state,
    validate_transition_map,
)
from fsm.rules.guards import (
    DEFAULT_GUARDS,
    guard_same_state,
    guard_terminal_state,
    guard_valid_state,
)

# Também importa diretamente para testar módulos individuais
from fsm.states.session import SessionState as DirectSessionState


class TestSessionStateAndTerminals:
    """
    Testa SessionState enum, TERMINAL_STATES, is_terminal e is_valid_state.
    Um teste cobre múltiplos componentes relacionados.
    """

    def test_session_state_enum_has_10_states_and_terminal_states_are_correct(self) -> None:
        """
        Verifica estrutura do enum e identificação de estados terminais.
        Cobre: SessionState, TERMINAL_STATES, is_terminal, is_valid_state
        """
        # Enum tem exatamente 10 estados
        all_states = list(SessionState)
        assert len(all_states) == 10

        # Estados não-terminais (4)
        non_terminal = {
            SessionState.INITIAL,
            SessionState.TRIAGE,
            SessionState.COLLECTING_INFO,
            SessionState.GENERATING_RESPONSE,
        }

        # Estados terminais (6)
        expected_terminals = {
            SessionState.HANDOFF_HUMAN,
            SessionState.SELF_SERVE_INFO,
            SessionState.ROUTE_EXTERNAL,
            SessionState.SCHEDULED_FOLLOWUP,
            SessionState.TIMEOUT,
            SessionState.ERROR,
        }

        # Valida TERMINAL_STATES
        assert expected_terminals == TERMINAL_STATES
        assert len(TERMINAL_STATES) == 6

        # Valida is_terminal para todos os estados
        for state in all_states:
            if state in expected_terminals:
                assert is_terminal(state) is True
                assert state in TERMINAL_STATES
            else:
                assert is_terminal(state) is False
                assert state in non_terminal

        # Valida is_valid_state
        for state in all_states:
            assert is_valid_state(state) is True

        # DEFAULT_INITIAL_STATE é INITIAL
        assert DEFAULT_INITIAL_STATE == SessionState.INITIAL
        assert DEFAULT_INITIAL_STATE in non_terminal

    def test_session_state_direct_import_matches_reexport(self) -> None:
        """Verifica que import direto e re-export são equivalentes."""
        assert DirectSessionState is SessionState
        assert DirectSessionState.INITIAL == SessionState.INITIAL

    def test_session_state_values_are_explicit_strings(self) -> None:
        """Estados devem possuir valores string estáveis para persistência."""
        for state in SessionState:
            assert state.value == state.name
            assert str(state) == state.name


class TestValidTransitionsAndRules:
    """
    Testa VALID_TRANSITIONS, get_valid_targets, is_transition_valid e validate_transition_map.
    """

    def test_valid_transitions_structure_and_terminal_states_have_no_exits(self) -> None:
        """
        Verifica estrutura de transições e que terminais não têm saída.
        Cobre: VALID_TRANSITIONS, TransitionMap, validate_transition_map
        """
        # Todos os estados estão no mapa
        for state in SessionState:
            assert state in VALID_TRANSITIONS

        # Estados terminais têm conjunto vazio
        for terminal in TERMINAL_STATES:
            assert VALID_TRANSITIONS[terminal] == frozenset()

        # Estados não-terminais têm ao menos uma transição
        non_terminals = set(SessionState) - TERMINAL_STATES
        for state in non_terminals:
            assert len(VALID_TRANSITIONS[state]) > 0

        # Mapa é válido (sem erros)
        errors = validate_transition_map()
        assert errors == []

    def test_get_valid_targets_and_is_transition_valid_consistency(self) -> None:
        """
        Verifica que get_valid_targets e is_transition_valid são consistentes.
        Cobre: get_valid_targets, is_transition_valid
        """
        for from_state in SessionState:
            valid_targets = get_valid_targets(from_state)

            for to_state in SessionState:
                expected = to_state in valid_targets
                actual = is_transition_valid(from_state, to_state)
                assert actual == expected, f"{from_state} → {to_state}"

    def test_specific_transition_paths_are_valid(self) -> None:
        """
        Verifica caminhos específicos de transição.
        Cobre: is_transition_valid em cenários reais
        """
        # Caminho feliz: INITIAL → TRIAGE → HANDOFF_HUMAN
        assert is_transition_valid(SessionState.INITIAL, SessionState.TRIAGE)
        assert is_transition_valid(SessionState.TRIAGE, SessionState.HANDOFF_HUMAN)

        # Caminho de coleta: TRIAGE → COLLECTING_INFO → GENERATING_RESPONSE
        assert is_transition_valid(SessionState.TRIAGE, SessionState.COLLECTING_INFO)
        assert is_transition_valid(SessionState.COLLECTING_INFO, SessionState.GENERATING_RESPONSE)

        # Loop de coleta permitido
        assert is_transition_valid(SessionState.COLLECTING_INFO, SessionState.COLLECTING_INFO)

        # Transições inválidas
        assert not is_transition_valid(SessionState.INITIAL, SessionState.HANDOFF_HUMAN)
        assert not is_transition_valid(SessionState.HANDOFF_HUMAN, SessionState.INITIAL)

        # Terminal não sai
        for terminal in TERMINAL_STATES:
            for state in SessionState:
                assert not is_transition_valid(terminal, state)


class TestGuardsAndEvaluation:
    """
    Testa guards individuais, GuardResult e evaluate_guards.
    """

    def test_guard_result_creation_and_properties(self) -> None:
        """
        Verifica criação de GuardResult.
        Cobre: GuardResult.allow(), GuardResult.deny()
        """
        # Allow
        result = GuardResult.allow()
        assert result.allowed is True
        assert result.reason is None

        # Deny
        result = GuardResult.deny("motivo do bloqueio")
        assert result.allowed is False
        assert result.reason == "motivo do bloqueio"

    def test_individual_guards_terminal_same_state_valid(self) -> None:
        """
        Testa guards individuais em diferentes cenários.
        Cobre: guard_terminal_state, guard_same_state, guard_valid_state
        """
        # guard_terminal_state: bloqueia saída de terminal
        result = guard_terminal_state(SessionState.HANDOFF_HUMAN, SessionState.TRIAGE)
        assert result.allowed is False

        result = guard_terminal_state(SessionState.TRIAGE, SessionState.HANDOFF_HUMAN)
        assert result.allowed is True

        # guard_same_state: bloqueia reflexiva exceto COLLECTING_INFO
        result = guard_same_state(SessionState.TRIAGE, SessionState.TRIAGE)
        assert result.allowed is False

        result = guard_same_state(SessionState.COLLECTING_INFO, SessionState.COLLECTING_INFO)
        assert result.allowed is True

        # guard_valid_state: valida tipos
        result = guard_valid_state(SessionState.INITIAL, SessionState.TRIAGE)
        assert result.allowed is True

    def test_evaluate_guards_combines_all_guards(self) -> None:
        """
        Testa evaluate_guards com múltiplos guards.
        Cobre: evaluate_guards, DEFAULT_GUARDS
        """
        # Transição válida passa todos os guards
        result = evaluate_guards(SessionState.INITIAL, SessionState.TRIAGE)
        assert result.allowed is True

        # Transição de terminal é bloqueada
        result = evaluate_guards(SessionState.ERROR, SessionState.INITIAL)
        assert result.allowed is False
        assert "terminal" in result.reason.lower()

        # DEFAULT_GUARDS está configurado
        assert len(DEFAULT_GUARDS) >= 3


class TestStateTransitionAndTransitionResult:
    """
    Testa StateTransition dataclass e TransitionResult.
    """

    def test_state_transition_creation_validation_and_log_dict(self) -> None:
        """
        Testa criação, validação e serialização de StateTransition.
        Cobre: StateTransition, to_log_dict, validações
        """
        # Criação válida
        transition = StateTransition(
            from_state=SessionState.INITIAL,
            to_state=SessionState.TRIAGE,
            trigger="user_message",
            metadata={"channel": "whatsapp"},
            confidence=0.95,
        )

        assert transition.from_state == SessionState.INITIAL
        assert transition.to_state == SessionState.TRIAGE
        assert transition.trigger == "user_message"
        assert transition.confidence == 0.95
        assert isinstance(transition.timestamp, datetime)

        # to_log_dict retorna dict seguro
        log = transition.to_log_dict()
        assert log["from_state"] == "INITIAL"
        assert log["to_state"] == "TRIAGE"
        assert log["trigger"] == "user_message"
        assert "timestamp" in log
        assert log["confidence"] == 0.95
        assert log["metadata"] == {"channel": "whatsapp"}

    def test_state_transition_validation_errors(self) -> None:
        """
        Testa validação de StateTransition.
        Cobre: __post_init__ validações
        """
        # confidence fora do range
        with pytest.raises(ValueError, match="confidence"):
            StateTransition(
                from_state=SessionState.INITIAL,
                to_state=SessionState.TRIAGE,
                trigger="test",
                confidence=1.5,
            )

        with pytest.raises(ValueError, match="confidence"):
            StateTransition(
                from_state=SessionState.INITIAL,
                to_state=SessionState.TRIAGE,
                trigger="test",
                confidence=-0.1,
            )

        # trigger vazio
        with pytest.raises(ValueError, match="trigger"):
            StateTransition(
                from_state=SessionState.INITIAL,
                to_state=SessionState.TRIAGE,
                trigger="",
            )

        with pytest.raises(ValueError, match="trigger"):
            StateTransition(
                from_state=SessionState.INITIAL,
                to_state=SessionState.TRIAGE,
                trigger="   ",
            )

    def test_transition_result_creation_and_validation(self) -> None:
        """
        Testa TransitionResult.
        Cobre: TransitionResult sucesso e falha
        """
        transition = StateTransition(
            from_state=SessionState.INITIAL,
            to_state=SessionState.TRIAGE,
            trigger="test",
        )

        # Sucesso com transition
        result = TransitionResult(success=True, transition=transition)
        assert result.success is True
        assert result.transition is not None
        assert result.error_reason is None

        # Falha com error_reason
        result = TransitionResult(success=False, error_reason="Transição inválida")
        assert result.success is False
        assert result.transition is None
        assert result.error_reason == "Transição inválida"

        # Validação: sucesso sem transition
        with pytest.raises(ValueError, match="deve incluir transition"):
            TransitionResult(success=True, transition=None)

        # Validação: falha sem error_reason
        with pytest.raises(ValueError, match="deve incluir error_reason"):
            TransitionResult(success=False, error_reason=None)


class TestFSMStateMachineCompleteFlow:
    """
    Testa FSMStateMachine e create_fsm com fluxos completos.
    """

    def test_create_fsm_and_initial_state(self) -> None:
        """
        Testa factory e estado inicial.
        Cobre: create_fsm, FSMStateMachine.__init__, INITIAL_STATES
        """
        fsm = create_fsm("session-123")

        assert fsm.current_state == SessionState.INITIAL
        assert fsm.session_id == "session-123"
        assert fsm.is_terminal is False
        assert len(fsm.history) == 0

        # INITIAL_STATES contém DEFAULT_INITIAL_STATE
        assert SessionState.INITIAL in INITIAL_STATES

        # Estado personalizado
        fsm2 = create_fsm("session-456", initial_state=SessionState.TRIAGE)
        assert fsm2.current_state == SessionState.TRIAGE

    def test_complete_happy_path_flow(self) -> None:
        """
        Testa fluxo completo:
        INITIAL → TRIAGE → COLLECTING_INFO → GENERATING_RESPONSE → SELF_SERVE_INFO.
        Cobre: transition, can_transition_to, history, get_state_summary, get_history_summary
        """
        fsm = create_fsm("test-happy-path")

        # Passo 1: INITIAL → TRIAGE
        assert fsm.can_transition_to(SessionState.TRIAGE)
        result = fsm.transition(SessionState.TRIAGE, trigger="first_message")
        assert result.success
        assert fsm.current_state == SessionState.TRIAGE

        # Passo 2: TRIAGE → COLLECTING_INFO
        result = fsm.transition(
            SessionState.COLLECTING_INFO,
            trigger="need_more_info",
            metadata={"question": "data_nascimento"},
        )
        assert result.success
        assert fsm.current_state == SessionState.COLLECTING_INFO

        # Passo 3: Loop de coleta
        result = fsm.transition(
            SessionState.COLLECTING_INFO,
            trigger="additional_info",
        )
        assert result.success

        # Passo 4: COLLECTING_INFO → GENERATING_RESPONSE
        result = fsm.transition(
            SessionState.GENERATING_RESPONSE,
            trigger="info_complete",
            confidence=0.9,
        )
        assert result.success

        # Passo 5: GENERATING_RESPONSE → SELF_SERVE_INFO (terminal)
        result = fsm.transition(
            SessionState.SELF_SERVE_INFO,
            trigger="response_sent",
        )
        assert result.success
        assert fsm.current_state == SessionState.SELF_SERVE_INFO
        assert fsm.is_terminal is True

        # Verifica histórico
        assert len(fsm.history) == 5

        # get_state_summary
        summary = fsm.get_state_summary()
        assert summary["current_state"] == "SELF_SERVE_INFO"
        assert summary["is_terminal"] is True
        assert summary["transition_count"] == 5
        assert summary["valid_targets"] == []

        # get_history_summary
        history = fsm.get_history_summary()
        assert len(history) == 5
        assert all("from_state" in t for t in history)
        assert all("trigger" in t for t in history)

    def test_terminal_state_blocks_all_transitions(self) -> None:
        """
        Testa que estados terminais não permitem saída.
        Cobre: transition em terminal, can_transition_to em terminal
        """
        fsm = create_fsm("test-terminal")

        # Vai para terminal
        fsm.transition(SessionState.TRIAGE, trigger="init")
        fsm.transition(SessionState.HANDOFF_HUMAN, trigger="escalate")

        assert fsm.is_terminal is True
        assert fsm.get_valid_targets() == frozenset()

        # Tenta todas as transições
        for state in SessionState:
            assert fsm.can_transition_to(state) is False

            result = fsm.transition(state, trigger="blocked")
            assert result.success is False
            assert result.error_reason is not None

    def test_invalid_transitions_are_rejected(self) -> None:
        """
        Testa rejeição de transições inválidas.
        """
        fsm = create_fsm("test-invalid")

        # INITIAL não pode ir direto para HANDOFF_HUMAN
        assert fsm.can_transition_to(SessionState.HANDOFF_HUMAN) is False

        result = fsm.transition(SessionState.HANDOFF_HUMAN, trigger="invalid")
        assert result.success is False
        assert "inválida" in result.error_reason.lower() or "invalid" in result.error_reason.lower()

        # Estado não mudou
        assert fsm.current_state == SessionState.INITIAL
        assert len(fsm.history) == 0

    def test_reset_clears_state_and_history(self) -> None:
        """
        Testa reset da FSM.
        Cobre: reset()
        """
        fsm = create_fsm("test-reset")
        fsm.transition(SessionState.TRIAGE, trigger="init")
        fsm.transition(SessionState.HANDOFF_HUMAN, trigger="escalate")

        assert len(fsm.history) == 2
        assert fsm.is_terminal is True

        # Reset
        fsm.reset()
        assert fsm.current_state == SessionState.INITIAL
        assert len(fsm.history) == 0
        assert fsm.is_terminal is False

        # Reset com estado customizado
        fsm.reset(new_initial_state=SessionState.TRIAGE)
        assert fsm.current_state == SessionState.TRIAGE

    def test_history_is_immutable_copy(self) -> None:
        """
        Verifica que history retorna cópia imutável.
        """
        fsm = create_fsm("test-immutable")
        fsm.transition(SessionState.TRIAGE, trigger="init")

        history1 = fsm.history
        history2 = fsm.history

        # São cópias diferentes
        assert history1 is not history2
        assert history1 == history2

        # Modificar não afeta interno
        history1.clear()
        assert len(fsm.history) == 1


class TestEdgeCasesAndBoundaries:
    """
    Testa casos de borda e condições limite.
    """

    def test_confidence_boundaries(self) -> None:
        """Testa valores limite de confidence."""
        # 0.0 é válido
        t = StateTransition(
            from_state=SessionState.INITIAL,
            to_state=SessionState.TRIAGE,
            trigger="test",
            confidence=0.0,
        )
        assert t.confidence == 0.0

        # 1.0 é válido
        t = StateTransition(
            from_state=SessionState.INITIAL,
            to_state=SessionState.TRIAGE,
            trigger="test",
            confidence=1.0,
        )
        assert t.confidence == 1.0

    def test_all_terminal_states_individually(self) -> None:
        """
        Testa cada estado terminal.
        """
        for terminal in TERMINAL_STATES:
            fsm = create_fsm(f"test-{terminal.name}")

            # Encontra caminho até o terminal
            if terminal in get_valid_targets(SessionState.INITIAL):
                fsm.transition(terminal, trigger="direct")
            elif terminal in get_valid_targets(SessionState.TRIAGE):
                fsm.transition(SessionState.TRIAGE, trigger="init")
                fsm.transition(terminal, trigger="to_terminal")
            elif terminal in get_valid_targets(SessionState.COLLECTING_INFO):
                fsm.transition(SessionState.TRIAGE, trigger="init")
                fsm.transition(SessionState.COLLECTING_INFO, trigger="collect")
                fsm.transition(terminal, trigger="to_terminal")
            elif terminal in get_valid_targets(SessionState.GENERATING_RESPONSE):
                fsm.transition(SessionState.TRIAGE, trigger="init")
                fsm.transition(SessionState.GENERATING_RESPONSE, trigger="gen")
                fsm.transition(terminal, trigger="to_terminal")

            assert fsm.is_terminal, f"{terminal.name} deveria ser terminal"
            assert fsm.current_state == terminal

    def test_metadata_in_transition(self) -> None:
        """Testa que metadata é preservado corretamente."""
        fsm = create_fsm("test-metadata")

        metadata = {
            "channel": "whatsapp",
            "tenant_id": "tenant-123",
            "event_type": "message",
        }

        fsm.transition(
            SessionState.TRIAGE,
            trigger="with_metadata",
            metadata=metadata,
        )

        assert fsm.history[0].metadata == metadata
        assert fsm.get_history_summary()[0]["metadata"] == metadata

    def test_session_id_in_summary(self) -> None:
        """Verifica session_id no summary."""
        fsm = create_fsm("my-session-id")
        summary = fsm.get_state_summary()
        assert summary["session_id"] == "my-session-id"

    def test_fsm_state_machine_direct_instantiation(self) -> None:
        """Testa instanciação direta (sem factory)."""
        fsm = FSMStateMachine(
            initial_state=SessionState.COLLECTING_INFO,
            session_id="direct-123",
        )
        assert fsm.current_state == SessionState.COLLECTING_INFO
        assert fsm.session_id == "direct-123"

    def test_default_values(self) -> None:
        """Testa valores default."""
        fsm = FSMStateMachine()
        assert fsm.current_state == SessionState.INITIAL
        assert fsm.session_id == ""

        t = StateTransition(
            from_state=SessionState.INITIAL,
            to_state=SessionState.TRIAGE,
            trigger="test",
        )
        assert t.confidence == 1.0
        assert t.metadata == {}
