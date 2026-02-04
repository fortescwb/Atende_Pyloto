"""
Máquina de estados (FSMStateMachine) para gerenciamento de sessões.

Este módulo implementa a FSM principal que controla transições
de estado e mantém histórico rastreável.

Referência: REGRAS_E_PADROES.md § 2.5 — FSM determinístico
Referência: FUNCIONAMENTO.md § 4.4 — FSM avalia estado e transições
Referência: AUDITORIA_ARQUITETURA.md § 9.2.3 — FSMStateMachine
"""

from typing import Any

from fsm.rules.guards import GuardResult, evaluate_guards
from fsm.states.session import (
    DEFAULT_INITIAL_STATE,
    SessionState,
    is_terminal,
)
from fsm.transitions.rules import get_valid_targets, is_transition_valid
from fsm.types.transition import StateTransition, TransitionResult


class FSMStateMachine:
    """
    Máquina de estados para sessões de atendimento.

    Gerencia o estado atual, valida transições e mantém
    histórico completo para auditoria.

    Attributes:
        current_state: Estado atual da máquina
        history: Histórico de transições realizadas
    """

    __slots__ = ("_current_state", "_history", "_session_id")

    def __init__(
        self,
        initial_state: SessionState | None = None,
        session_id: str = "",
    ) -> None:
        """
        Inicializa a máquina de estados.

        Args:
            initial_state: Estado inicial (usa DEFAULT_INITIAL_STATE se None)
            session_id: Identificador da sessão para logs
        """
        self._current_state = initial_state or DEFAULT_INITIAL_STATE
        self._history: list[StateTransition] = []
        self._session_id = session_id

    @property
    def current_state(self) -> SessionState:
        """Estado atual da máquina."""
        return self._current_state

    @property
    def history(self) -> list[StateTransition]:
        """Histórico de transições (cópia para evitar mutação externa)."""
        return list(self._history)

    @property
    def session_id(self) -> str:
        """Identificador da sessão."""
        return self._session_id

    @property
    def is_terminal(self) -> bool:
        """Verifica se está em estado terminal."""
        return is_terminal(self._current_state)

    def can_transition_to(self, target: SessionState) -> bool:
        """Verifica se pode transitar para o estado alvo."""
        if not is_transition_valid(self._current_state, target):
            return False
        result = evaluate_guards(self._current_state, target)
        return result.allowed

    def get_valid_targets(self) -> frozenset[SessionState]:
        """Retorna estados de destino válidos a partir do estado atual."""
        return get_valid_targets(self._current_state)

    def transition(
        self,
        target: SessionState,
        trigger: str,
        metadata: dict[str, Any] | None = None,
        confidence: float = 1.0,
    ) -> TransitionResult:
        """
        Tenta realizar uma transição de estado.

        Args:
            target: Estado de destino
            trigger: Identificador do gatilho (ex: 'user_message', 'ai_decision')
            metadata: Dados adicionais para auditoria (nunca PII)
            confidence: Nível de confiança na transição (0.0 a 1.0)

        Returns:
            TransitionResult com sucesso/falha e dados da transição
        """
        # Valida regra de transição primeiro
        if not is_transition_valid(self._current_state, target):
            return TransitionResult(
                success=False,
                error_reason=(
                    f"Transição inválida: {self._current_state.name} → {target.name}"
                ),
            )

        # Avalia guards
        guard_result: GuardResult = evaluate_guards(self._current_state, target)
        if not guard_result.allowed:
            return TransitionResult(
                success=False,
                error_reason=guard_result.reason,
            )

        # Cria registro da transição
        transition = StateTransition(
            from_state=self._current_state,
            to_state=target,
            trigger=trigger,
            metadata=metadata or {},
            confidence=confidence,
        )

        # Efetua a transição
        self._current_state = target
        self._history.append(transition)

        return TransitionResult(success=True, transition=transition)

    def get_state_summary(self) -> dict[str, Any]:
        """
        Retorna resumo do estado atual para observability.

        Returns:
            Dict com informações do estado (seguro para logs)
        """
        return {
            "session_id": self._session_id,
            "current_state": self._current_state.name,
            "is_terminal": self.is_terminal,
            "transition_count": len(self._history),
            "valid_targets": [s.name for s in self.get_valid_targets()],
        }

    def get_history_summary(self) -> list[dict[str, Any]]:
        """
        Retorna histórico em formato seguro para logs.

        Returns:
            Lista de transições em formato dict
        """
        return [t.to_log_dict() for t in self._history]

    def reset(self, new_initial_state: SessionState | None = None) -> None:
        """
        Reseta a máquina para estado inicial.

        ATENÇÃO: Limpa todo o histórico. Usar com cautela.

        Args:
            new_initial_state: Novo estado inicial (usa default se None)
        """
        self._current_state = new_initial_state or DEFAULT_INITIAL_STATE
        self._history = []


def create_fsm(
    session_id: str,
    initial_state: SessionState | None = None,
) -> FSMStateMachine:
    """
    Factory function para criar uma FSM.

    Args:
        session_id: Identificador da sessão
        initial_state: Estado inicial (opcional)

    Returns:
        FSMStateMachine configurada
    """
    return FSMStateMachine(
        initial_state=initial_state,
        session_id=session_id,
    )


# Constantes re-exportadas para conveniência
INITIAL_STATES = frozenset({DEFAULT_INITIAL_STATE})
