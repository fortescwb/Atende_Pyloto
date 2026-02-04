"""
Regras de transição válidas entre estados da FSM.

Este módulo define quais transições são permitidas entre estados,
formando o grafo de transições da máquina de estados.

Referência: REGRAS_E_PADROES.md § 2.5 — FSM determinístico
Referência: AUDITORIA_ARQUITETURA.md § 9.2.3 — VALID_TRANSITIONS
"""

from fsm.states.session import TERMINAL_STATES, SessionState

# Tipagem explícita do mapa de transições
TransitionMap = dict[SessionState, frozenset[SessionState]]

# Mapa de transições válidas
# Chave: estado de origem
# Valor: conjunto de estados de destino permitidos
VALID_TRANSITIONS: TransitionMap = {
    # INITIAL: Pode iniciar triagem ou falhar
    SessionState.INITIAL: frozenset({
        SessionState.TRIAGE,
        SessionState.ERROR,
        SessionState.TIMEOUT,
    }),

    # TRIAGE: Pode coletar info, gerar resposta, escalar ou encerrar
    SessionState.TRIAGE: frozenset({
        SessionState.COLLECTING_INFO,
        SessionState.GENERATING_RESPONSE,
        SessionState.HANDOFF_HUMAN,
        SessionState.SELF_SERVE_INFO,
        SessionState.ROUTE_EXTERNAL,
        SessionState.ERROR,
        SessionState.TIMEOUT,
    }),

    # COLLECTING_INFO: Pode continuar coletando, gerar resposta ou encerrar
    SessionState.COLLECTING_INFO: frozenset({
        SessionState.COLLECTING_INFO,  # Permite loop para coleta adicional
        SessionState.GENERATING_RESPONSE,
        SessionState.HANDOFF_HUMAN,
        SessionState.ROUTE_EXTERNAL,
        SessionState.SCHEDULED_FOLLOWUP,
        SessionState.ERROR,
        SessionState.TIMEOUT,
    }),

    # GENERATING_RESPONSE: Pode encerrar com resposta, escalar ou agendar
    SessionState.GENERATING_RESPONSE: frozenset({
        SessionState.SELF_SERVE_INFO,
        SessionState.HANDOFF_HUMAN,
        SessionState.ROUTE_EXTERNAL,
        SessionState.SCHEDULED_FOLLOWUP,
        SessionState.ERROR,
    }),

    # Estados terminais: não permitem transição para outros estados
    SessionState.HANDOFF_HUMAN: frozenset(),
    SessionState.SELF_SERVE_INFO: frozenset(),
    SessionState.ROUTE_EXTERNAL: frozenset(),
    SessionState.SCHEDULED_FOLLOWUP: frozenset(),
    SessionState.TIMEOUT: frozenset(),
    SessionState.ERROR: frozenset(),
}


def get_valid_targets(state: SessionState) -> frozenset[SessionState]:
    """
    Retorna os estados de destino válidos para um estado de origem.

    Args:
        state: Estado de origem

    Returns:
        Conjunto de estados de destino permitidos (vazio se terminal)
    """
    return VALID_TRANSITIONS.get(state, frozenset())


def is_transition_valid(from_state: SessionState, to_state: SessionState) -> bool:
    """
    Verifica se uma transição é válida segundo as regras definidas.

    Args:
        from_state: Estado de origem
        to_state: Estado de destino

    Returns:
        True se a transição é permitida, False caso contrário
    """
    # Estados terminais nunca permitem saída
    if from_state in TERMINAL_STATES:
        return False

    valid_targets = get_valid_targets(from_state)
    return to_state in valid_targets


def validate_transition_map() -> list[str]:
    """
    Valida a integridade do mapa de transições.

    Verifica:
    - Todos os estados do enum estão no mapa
    - Estados terminais têm conjunto vazio
    - Nenhuma transição aponta para estado inexistente

    Returns:
        Lista de erros encontrados (vazia se válido)
    """
    errors: list[str] = []

    # Verifica se todos os estados estão no mapa
    for state in SessionState:
        if state not in VALID_TRANSITIONS:
            errors.append(f"Estado {state.name} ausente em VALID_TRANSITIONS")

    # Verifica estados terminais
    for state in TERMINAL_STATES:
        targets = VALID_TRANSITIONS.get(state, frozenset())
        if targets:
            errors.append(
                f"Estado terminal {state.name} não deveria ter transições: {targets}"
            )

    # Verifica se todos os destinos são estados válidos
    for from_state, targets in VALID_TRANSITIONS.items():
        for target in targets:
            if not isinstance(target, SessionState):
                errors.append(
                    f"Transição {from_state.name} → {target}: destino inválido"
                )

    return errors
