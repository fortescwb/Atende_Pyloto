"""
Estados canônicos de sessão para o fluxo de atendimento.

Este módulo define os estados que uma sessão pode assumir durante
seu ciclo de vida. Estados são determinísticos e explícitos.

Referência: REGRAS_E_PADROES.md § 2.5 — FSM determinístico
Referência: FUNCIONAMENTO.md § 4.4 — FSM avalia estado e transições
"""

from enum import Enum, auto


class SessionState(Enum):
    """
    Estados canônicos de uma sessão de atendimento.

    Baseado na análise de pyloto_corp (AUDITORIA_ARQUITETURA.md § 9.2.2),
    com adaptações para o novo repositório.

    Estados não-terminais:
        - INITIAL: Sessão recém-criada, aguardando primeiro evento
        - TRIAGE: Classificação/triagem em andamento
        - COLLECTING_INFO: Coleta estruturada de informações do usuário
        - GENERATING_RESPONSE: Preparando resposta ao usuário

    Estados terminais:
        - HANDOFF_HUMAN: Escalado para atendimento humano
        - SELF_SERVE_INFO: Atendido com informação (autoatendimento)
        - ROUTE_EXTERNAL: Encaminhado para sistema/recurso externo
        - SCHEDULED_FOLLOWUP: Follow-up agendado para retorno
        - TIMEOUT: Sessão expirou por inatividade
        - ERROR: Falha interna irrecuperável
    """

    # Estados não-terminais (fluxo em andamento)
    INITIAL = auto()
    TRIAGE = auto()
    COLLECTING_INFO = auto()
    GENERATING_RESPONSE = auto()

    # Estados terminais (sessão encerrada)
    HANDOFF_HUMAN = auto()
    SELF_SERVE_INFO = auto()
    ROUTE_EXTERNAL = auto()
    SCHEDULED_FOLLOWUP = auto()
    TIMEOUT = auto()
    ERROR = auto()


# Conjunto de estados que indicam término do fluxo
# Uma vez em estado terminal, a sessão não pode transitar para outro estado
TERMINAL_STATES: frozenset[SessionState] = frozenset({
    SessionState.HANDOFF_HUMAN,
    SessionState.SELF_SERVE_INFO,
    SessionState.ROUTE_EXTERNAL,
    SessionState.SCHEDULED_FOLLOWUP,
    SessionState.TIMEOUT,
    SessionState.ERROR,
})

# Estado inicial padrão para novas sessões
DEFAULT_INITIAL_STATE: SessionState = SessionState.INITIAL


def is_terminal(state: SessionState) -> bool:
    """
    Verifica se o estado é terminal (sessão encerrada).

    Args:
        state: Estado a ser verificado

    Returns:
        True se o estado é terminal, False caso contrário
    """
    return state in TERMINAL_STATES


def is_valid_state(state: SessionState) -> bool:
    """
    Verifica se o valor é um estado válido do enum.

    Args:
        state: Estado a ser verificado

    Returns:
        True se é um SessionState válido
    """
    return isinstance(state, SessionState)
