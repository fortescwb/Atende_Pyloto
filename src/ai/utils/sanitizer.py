"""Sanitização de conteúdo com PII (mascaramento de dados sensíveis).

Responsabilidade:
- Mascarar CPF, CNPJ, e-mails, telefones BR
- Aplicar defesa em profundidade (múltiplos pontos no pipeline)
- Garantir determinismo (mesma entrada = mesma saída)

Conforme REGRAS_E_PADROES.md § 6: logs sem PII.
Conforme REGRAS_E_PADROES.md § 1.5: defesa em profundidade.
"""

from __future__ import annotations

import re
from re import Pattern
from typing import Final

# Compilar patterns uma vez (performance + determinismo)
_PATTERNS: Final[dict[str, Pattern[str]]] = {
    # CPF: 123.456.789-10 ou 12345678910
    "cpf": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    # CNPJ: 12.345.678/0001-90 ou 12345678000190
    "cnpj": re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"),
    # E-mail
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    # Telefone BR: +55 11 98765-4321, (11) 98765-4321, etc
    "phone": re.compile(
        r"\+?55\s*\(?(\d{2})\)?\s*(?:9)?\d{4}-?\d{4}|"
        r"\(?(\d{2})\)?\s*(?:9)?\d{4}-?\d{4}|"
        r"\b9\d{4}-?\d{4}\b"
    ),
}

# Máscaras aplicadas
_MASKS: Final[dict[str, str]] = {
    "cpf": "[CPF]",
    "cnpj": "[CNPJ]",
    "email": "[EMAIL]",
    "phone": "[PHONE]",
}


def sanitize_pii(text: str) -> str:
    """Mascara PII em texto.

    Substitui padrões identificados por máscaras determinísticas.

    Args:
        text: Texto potencialmente contendo PII

    Returns:
        Texto com PII mascarado (determinístico: mesma entrada = mesma saída)

    Exemplos:
        >>> sanitize_pii("Meu CPF é 123.456.789-10")
        'Meu CPF é [CPF]'

        >>> sanitize_pii("Contate em john@example.com")
        'Contate em [EMAIL]'
    """
    if not text:
        return text

    result = text

    # Aplicar máscaras na ordem: específico → genérico
    for pii_type, pattern in _PATTERNS.items():
        result = pattern.sub(_MASKS[pii_type], result)

    return result


def mask_history(messages: list[str], max_messages: int = 5) -> list[str]:
    """Mascara PII em histórico de mensagens antes de enviar para LLM.

    Trunca para últimas N mensagens (minimização de dados) e mascara cada uma.

    Args:
        messages: Lista de strings com histórico de conversa
        max_messages: Número máximo de mensagens a manter (padrão 5)

    Returns:
        Lista mascarada e truncada

    Exemplos:
        >>> mask_history(["Meu CPF: 123.456.789-10", "Ok"])
        ['Meu CPF: [CPF]', 'Ok']
    """
    if not messages:
        return []

    # Truncar para últimas N mensagens (determinístico, limite de tokens)
    truncated = messages[-max_messages:] if len(messages) > max_messages else messages

    # Sanitizar cada mensagem
    return [sanitize_pii(msg) for msg in truncated]


def contains_pii(text: str) -> bool:
    """Verifica se texto contém PII detectável.

    Args:
        text: Texto a verificar

    Returns:
        True se algum padrão de PII foi encontrado
    """
    if not text:
        return False

    return any(pattern.search(text) for pattern in _PATTERNS.values())
