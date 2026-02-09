"""Cobertura adicional para guard denial na FSMStateMachine."""

from __future__ import annotations

import fsm.manager.machine as machine_module
from fsm.manager.machine import FSMStateMachine
from fsm.rules.guards import GuardResult
from fsm.states import SessionState


def test_transition_returns_failure_when_guard_blocks_valid_transition(
    monkeypatch,
) -> None:
    def _deny_guard(from_state: SessionState, to_state: SessionState) -> GuardResult:
        del from_state, to_state
        return GuardResult.deny("blocked_by_guard")

    monkeypatch.setattr(machine_module, "evaluate_guards", _deny_guard)

    machine = FSMStateMachine(initial_state=SessionState.INITIAL, session_id="sess-guard")
    result = machine.transition(target=SessionState.TRIAGE, trigger="test")

    assert result.success is False
    assert result.error_reason == "blocked_by_guard"
    assert machine.current_state == SessionState.INITIAL
