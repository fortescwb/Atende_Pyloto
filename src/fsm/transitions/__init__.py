"""
Exports públicos do módulo fsm/transitions.

Regras de transição válidas entre estados da FSM.
"""

from fsm.transitions.rules import (
    VALID_TRANSITIONS,
    TransitionMap,
    get_valid_targets,
    is_transition_valid,
    validate_transition_map,
)

__all__ = [
    "VALID_TRANSITIONS",
    "TransitionMap",
    "get_valid_targets",
    "is_transition_valid",
    "validate_transition_map",
]
