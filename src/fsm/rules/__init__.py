"""
Exports públicos do módulo fsm/rules.

Guards e invariantes para transições de estado.
"""

from fsm.rules.guards import (
    DEFAULT_GUARDS,
    GuardResult,
    TransitionContext,
    evaluate_guards,
    guard_same_state,
    guard_terminal_state,
    guard_valid_state,
)

__all__ = [
    "DEFAULT_GUARDS",
    "GuardResult",
    "TransitionContext",
    "evaluate_guards",
    "guard_same_state",
    "guard_terminal_state",
    "guard_valid_state",
]
