"""
Exports públicos do módulo fsm/states.

Estados canônicos de sessão para o fluxo de atendimento.
"""

from fsm.states.session import (
    DEFAULT_INITIAL_STATE,
    TERMINAL_STATES,
    SessionState,
    is_terminal,
    is_valid_state,
)

__all__ = [
    "DEFAULT_INITIAL_STATE",
    "TERMINAL_STATES",
    "SessionState",
    "is_terminal",
    "is_valid_state",
]
