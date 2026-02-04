"""Prompts de validação e revisão.

Define prompts para casos que requerem validação especial.
"""

from __future__ import annotations

# =============================================================================
# PROMPTS DE VALIDAÇÃO
# =============================================================================

VALIDATION_PROMPTS: dict[str, str] = {
    "LOW_CONFIDENCE": """A confiança da resposta está baixa.
Recomenda-se revisão humana antes de enviar.""",
    "SENSITIVE_TOPIC": """Este tópico pode ser sensível.
Tenha cuidado extra com a resposta.""",
    "POTENTIAL_COMPLAINT": """Pode ser uma reclamação.
Seja empático e ofereça soluções.""",
    "ESCALATION_NEEDED": """O usuário pode precisar de escalação.
Considere transferir para um humano.""",
    "PAYMENT_RELATED": """Assunto relacionado a pagamento.
Seja preciso com valores e datas.""",
    "LEGAL_QUESTION": """Pode ser uma questão legal.
Não dê conselhos jurídicos, encaminhe.""",
    "DATA_PRIVACY": """Questão sobre privacidade de dados.
Siga LGPD e políticas de privacidade.""",
}


def get_validation_context(validation_type: str) -> str:
    """Retorna contexto de validação.

    Args:
        validation_type: Tipo de validação

    Returns:
        Contexto para adicionar ao prompt
    """
    return VALIDATION_PROMPTS.get(validation_type, "")


# =============================================================================
# KEYWORDS SENSÍVEIS
# =============================================================================

SENSITIVE_KEYWORDS: tuple[str, ...] = (
    # Reclamações
    "reclamação",
    "reclamar",
    "processar",
    "advogado",
    "procon",
    "reclame aqui",
    # Cancelamento
    "cancelar",
    "encerrar",
    "desistir",
    "não quero mais",
    # Problemas
    "não funciona",
    "não está funcionando",
    "erro",
    "bug",
    "problema grave",
    # Urgência
    "urgente",
    "emergência",
    "imediato",
    # Financeiro
    "reembolso",
    "estorno",
    "devolução",
    "cobrado errado",
    "cobrança indevida",
    # Legal
    "processo",
    "justiça",
    "tribunal",
    "lgpd",
    "meus dados",
)

ESCALATION_KEYWORDS: tuple[str, ...] = (
    "falar com humano",
    "falar com atendente",
    "falar com pessoa",
    "quero um humano",
    "atendimento humano",
    "supervisor",
    "gerente",
    "responsável",
)


def contains_sensitive_content(text: str) -> bool:
    """Verifica se texto contém conteúdo sensível.

    Args:
        text: Texto a verificar

    Returns:
        True se contém keywords sensíveis
    """
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in SENSITIVE_KEYWORDS)


def requires_escalation(text: str) -> bool:
    """Verifica se texto indica necessidade de escalação.

    Args:
        text: Texto a verificar

    Returns:
        True se indica escalação
    """
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in ESCALATION_KEYWORDS)


def get_sensitivity_level(text: str) -> str:
    """Determina nível de sensibilidade do texto.

    Args:
        text: Texto a analisar

    Returns:
        Nível: "low", "medium", "high", "critical"
    """
    if requires_escalation(text):
        return "high"

    text_lower = text.lower()

    # Keywords críticos
    critical_keywords = ("processo", "justiça", "advogado", "procon")
    if any(kw in text_lower for kw in critical_keywords):
        return "critical"

    # Keywords de alta sensibilidade
    high_keywords = ("reclamação", "reembolso", "cobrado errado")
    if any(kw in text_lower for kw in high_keywords):
        return "high"

    # Keywords de média sensibilidade
    if contains_sensitive_content(text):
        return "medium"

    return "low"
