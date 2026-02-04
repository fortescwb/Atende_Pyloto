"""Prompts específicos por estado da FSM.

Define prompts customizados para cada estado do fluxo.
"""

from __future__ import annotations

# =============================================================================
# PROMPTS POR ESTADO
# =============================================================================

STATE_SPECIFIC_PROMPTS: dict[str, str] = {
    "ENTRY": """O usuário está iniciando uma nova conversa.
Seja receptivo e ajude a identificar a necessidade.""",
    "AWAITING_NAME": """O usuário precisa fornecer seu nome.
Seja educado ao solicitar essa informação.""",
    "AWAITING_DOCUMENT": """O usuário precisa fornecer um documento (CPF/CNPJ).
Explique o motivo e garanta sigilo.""",
    "AWAITING_CONFIRMATION": """O usuário precisa confirmar uma ação.
Seja claro sobre o que está sendo confirmado.""",
    "MENU_SELECTION": """O usuário está em um menu de opções.
Ajude-o a escolher a melhor opção.""",
    "SUPPORT_TICKET": """O usuário está em um ticket de suporte.
Colete informações relevantes para resolução.""",
    "SCHEDULING": """O usuário está agendando algo.
Confirme data, hora e detalhes.""",
    "PAYMENT_PENDING": """O usuário tem um pagamento pendente.
Seja claro sobre valores e opções.""",
    "HUMAN_HANDOFF": """O usuário será transferido para um humano.
Informe sobre o processo e tempo de espera.""",
    "COMPLETED": """A conversa foi concluída com sucesso.
Agradeça e ofereça ajuda adicional.""",
    "ERROR": """Ocorreu um erro no sistema.
Peça desculpas e ofereça alternativas.""",
}

DEFAULT_STATE_PROMPT = """Estado atual da conversa não reconhecido.
Seja prestativo e tente entender a necessidade do usuário."""


def get_state_context(state: str) -> str:
    """Retorna contexto específico do estado.

    Args:
        state: Nome do estado atual

    Returns:
        Contexto para adicionar ao prompt
    """
    return STATE_SPECIFIC_PROMPTS.get(state, DEFAULT_STATE_PROMPT)


# =============================================================================
# INTENTS POR ESTADO
# =============================================================================

STATE_EXPECTED_INTENTS: dict[str, tuple[str, ...]] = {
    "ENTRY": (
        "GREETING",
        "SUPPORT_REQUEST",
        "PRICING_INQUIRY",
        "SCHEDULE_REQUEST",
        "INFORMATION_REQUEST",
        "COMPLAINT",
        "OTHER",
    ),
    "AWAITING_NAME": (
        "NAME_PROVIDED",
        "REFUSE_NAME",
        "QUESTION",
        "CANCEL",
    ),
    "AWAITING_DOCUMENT": (
        "DOCUMENT_PROVIDED",
        "REFUSE_DOCUMENT",
        "QUESTION",
        "CANCEL",
    ),
    "AWAITING_CONFIRMATION": (
        "CONFIRM_YES",
        "CONFIRM_NO",
        "QUESTION",
        "CANCEL",
    ),
    "MENU_SELECTION": (
        "OPTION_SELECTED",
        "QUESTION",
        "GO_BACK",
        "CANCEL",
    ),
    "SUPPORT_TICKET": (
        "INFORMATION_PROVIDED",
        "QUESTION",
        "ESCALATE",
        "CANCEL",
    ),
    "SCHEDULING": (
        "DATE_PROVIDED",
        "TIME_PROVIDED",
        "RESCHEDULE",
        "CANCEL",
    ),
    "PAYMENT_PENDING": (
        "PAYMENT_CONFIRMED",
        "PAYMENT_QUESTION",
        "PAYMENT_ISSUE",
        "CANCEL",
    ),
}


def get_expected_intents(state: str) -> tuple[str, ...]:
    """Retorna intents esperados para um estado.

    Args:
        state: Nome do estado atual

    Returns:
        Tuple de intents possíveis
    """
    return STATE_EXPECTED_INTENTS.get(
        state,
        ("UNKNOWN", "QUESTION", "CANCEL"),
    )


def is_intent_expected(state: str, intent: str) -> bool:
    """Verifica se intent é esperado para o estado.

    Args:
        state: Nome do estado atual
        intent: Intent detectado

    Returns:
        True se intent é esperado
    """
    expected = get_expected_intents(state)
    return intent in expected
