"""
Módulo FSM — Máquina de Estados para sessões de atendimento.

Este módulo implementa a FSM determinística que governa
as transições de estado das sessões.

Estrutura:
    - states/: Definições dos estados (SessionState enum)
    - transitions/: Regras de transição (VALID_TRANSITIONS)
    - rules/: Guards e invariantes
    - manager/: Máquina de estados (FSMStateMachine)
    - types/: Tipos de dados (StateTransition, TransitionResult)

Referência: REGRAS_E_PADROES.md § 2.5
Referência: FUNCIONAMENTO.md § 4.4
"""

# Estados
# Manager
from fsm.manager import (
    INITIAL_STATES,
    FSMStateMachine,
    create_fsm,
)

# Guards/Rules
from fsm.rules import (
    GuardResult,
    evaluate_guards,
)
from fsm.states import (
    DEFAULT_INITIAL_STATE,
    TERMINAL_STATES,
    SessionState,
    is_terminal,
    is_valid_state,
)

# Transições
from fsm.transitions import (
    VALID_TRANSITIONS,
    get_valid_targets,
    is_transition_valid,
    validate_transition_map,
)

# Types
from fsm.types import (
    StateTransition,
    TransitionResult,
)

__all__ = [
    "DEFAULT_INITIAL_STATE",
    "INITIAL_STATES",
    "TERMINAL_STATES",
    # Transições
    "VALID_TRANSITIONS",
    # Manager
    "FSMStateMachine",
    # Guards
    "GuardResult",
    # Estados
    "SessionState",
    # Types
    "StateTransition",
    "TransitionResult",
    "create_fsm",
    "evaluate_guards",
    "get_valid_targets",
    "is_terminal",
    "is_transition_valid",
    "is_valid_state",
    "validate_transition_map",
]
