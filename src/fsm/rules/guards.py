"""
Guards e invariantes para transições de estado.

Este módulo define regras adicionais (guards) que podem bloquear
ou permitir transições baseado em condições de contexto.

Referência: REGRAS_E_PADROES.md § 1.5 — Defesa em profundidade
Referência: FUNCIONAMENTO.md § 7 — Segurança
"""

from typing import Any, Protocol

from fsm.states.session import TERMINAL_STATES, SessionState


class TransitionContext(Protocol):
    """
    Protocolo que define o contexto necessário para avaliar guards.

    O contexto é passado pelo caller e contém informações
    relevantes para decidir se uma transição deve ocorrer.
    """

    @property
    def session_id(self) -> str:
        """Identificador único da sessão."""
        ...

    @property
    def current_state(self) -> SessionState:
        """Estado atual da sessão."""
        ...

    @property
    def message_count(self) -> int:
        """Quantidade de mensagens na sessão."""
        ...

    @property
    def metadata(self) -> dict[str, Any]:
        """Metadados adicionais do contexto."""
        ...


class GuardResult:
    """
    Resultado da avaliação de um guard.

    Attributes:
        allowed: Se a transição é permitida
        reason: Motivo do bloqueio (se allowed=False)
    """

    __slots__ = ("allowed", "reason")

    def __init__(self, allowed: bool, reason: str | None = None) -> None:
        self.allowed = allowed
        self.reason = reason

    @classmethod
    def allow(cls) -> "GuardResult":
        """Cria resultado permitindo a transição."""
        return cls(allowed=True)

    @classmethod
    def deny(cls, reason: str) -> "GuardResult":
        """Cria resultado negando a transição."""
        return cls(allowed=False, reason=reason)


def guard_terminal_state(
    from_state: SessionState,
    to_state: SessionState,
) -> GuardResult:
    """
    Guard: Estados terminais não permitem saída.

    Args:
        from_state: Estado de origem
        to_state: Estado de destino (não usado, mas necessário para assinatura)

    Returns:
        GuardResult indicando se transição é permitida
    """
    if from_state in TERMINAL_STATES:
        return GuardResult.deny(
            f"Estado {from_state.name} é terminal, não permite transição"
        )
    return GuardResult.allow()


def guard_same_state(
    from_state: SessionState,
    to_state: SessionState,
) -> GuardResult:
    """
    Guard: Previne transição para o mesmo estado (exceto casos explícitos).

    Transições para o mesmo estado são permitidas apenas para
    COLLECTING_INFO (loop de coleta).

    Args:
        from_state: Estado de origem
        to_state: Estado de destino

    Returns:
        GuardResult indicando se transição é permitida
    """
    # COLLECTING_INFO pode transitar para si mesmo (coleta adicional)
    if from_state == SessionState.COLLECTING_INFO:
        return GuardResult.allow()

    if from_state == to_state:
        return GuardResult.deny(
            f"Transição reflexiva não permitida: {from_state.name} → {to_state.name}"
        )

    return GuardResult.allow()


def guard_valid_state(
    from_state: SessionState,
    to_state: SessionState,
) -> GuardResult:
    """
    Guard: Verifica se ambos os estados são válidos.

    Args:
        from_state: Estado de origem
        to_state: Estado de destino

    Returns:
        GuardResult indicando se transição é permitida
    """
    if not isinstance(from_state, SessionState):
        return GuardResult.deny(f"Estado de origem inválido: {from_state}")

    if not isinstance(to_state, SessionState):
        return GuardResult.deny(f"Estado de destino inválido: {to_state}")

    return GuardResult.allow()


# Lista de guards a serem aplicados em ordem
# Todos devem retornar allow() para a transição prosseguir
DEFAULT_GUARDS = [
    guard_valid_state,
    guard_terminal_state,
    guard_same_state,
]


def evaluate_guards(
    from_state: SessionState,
    to_state: SessionState,
    guards: list | None = None,
) -> GuardResult:
    """
    Avalia todos os guards para uma transição.

    Args:
        from_state: Estado de origem
        to_state: Estado de destino
        guards: Lista de guards a aplicar (usa DEFAULT_GUARDS se None)

    Returns:
        GuardResult do primeiro guard que negar, ou allow() se todos passarem
    """
    guards_to_apply = guards if guards is not None else DEFAULT_GUARDS

    for guard in guards_to_apply:
        result = guard(from_state, to_state)
        if not result.allowed:
            return result

    return GuardResult.allow()
