"""
Exports públicos do módulo fsm/manager.

Máquina de estados (FSMStateMachine) para gerenciamento de sessões.
"""

from fsm.manager.machine import (
    INITIAL_STATES,
    FSMStateMachine,
    create_fsm,
)

__all__ = [
    "INITIAL_STATES",
    "FSMStateMachine",
    "create_fsm",
]
