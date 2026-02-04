"""Extrator de dados do lead a partir de mensagens.

Extrai informações como nome, email e telefone
das mensagens do usuário de forma determinística (regex).

Conforme TODO_llm.md § P1.5: Extração automática de dados.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class ExtractedLeadData:
    """Dados extraídos de uma mensagem.

    Contém campos opcionais que podem ser extraídos.
    Cada campo é None se não foi encontrado na mensagem.
    """

    name: str | None = None
    email: str | None = None
    phone: str | None = None


# Padrões de regex para extração
_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    re.IGNORECASE,
)

# Telefone brasileiro (com ou sem código de país)
_PHONE_PATTERN = re.compile(
    r"(?:\+?55\s?)?(?:\(?\d{2}\)?[\s.-]?)?\d{4,5}[\s.-]?\d{4}\b"
)

# Padrões para detectar nome (após frases comuns)
_NAME_PATTERN_1 = r"(?:meu nome [ée]\s*|me chamo\s*|sou o\s*|sou a\s*)"
_NAME_PATTERN_2 = r"([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+)?)"
_NAME_PATTERNS = [
    re.compile(_NAME_PATTERN_1 + _NAME_PATTERN_2, re.IGNORECASE),
    re.compile(r"(?:pode me chamar de\s*|chama de\s*)([A-Za-zÀ-ÿ]+)", re.IGNORECASE),
]


def extract_email(text: str) -> str | None:
    """Extrai primeiro email encontrado no texto.

    Args:
        text: Texto para análise

    Returns:
        Email encontrado ou None
    """
    match = _EMAIL_PATTERN.search(text)
    return match.group(0).lower() if match else None


def extract_phone(text: str) -> str | None:
    """Extrai primeiro telefone encontrado no texto.

    Normaliza para formato sem espaços/pontuação.

    Args:
        text: Texto para análise

    Returns:
        Telefone normalizado ou None
    """
    match = _PHONE_PATTERN.search(text)
    if not match:
        return None

    # Normaliza removendo caracteres não-numéricos
    phone = re.sub(r"[^\d]", "", match.group(0))

    # Valida tamanho mínimo (8 dígitos local, até 13 com país)
    if len(phone) < 8 or len(phone) > 13:
        return None

    return phone


def extract_name(text: str) -> str | None:
    """Extrai nome do usuário se mencionado no texto.

    Busca padrões como "meu nome é X", "me chamo X", etc.

    Args:
        text: Texto para análise

    Returns:
        Nome encontrado ou None
    """
    for pattern in _NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            name = match.group(1).strip()
            # Valida que tem pelo menos 2 caracteres
            if len(name) >= 2:
                return name.title()

    return None


def extract_lead_data(text: str) -> ExtractedLeadData:
    """Extrai todos os dados possíveis de uma mensagem.

    Args:
        text: Texto da mensagem do usuário

    Returns:
        ExtractedLeadData com campos encontrados
    """
    return ExtractedLeadData(
        name=extract_name(text),
        email=extract_email(text),
        phone=extract_phone(text),
    )


def merge_lead_data(
    existing: ExtractedLeadData | None,
    new: ExtractedLeadData,
) -> ExtractedLeadData:
    """Mescla dados existentes com novos (prioriza novos se presentes).

    Args:
        existing: Dados já coletados (pode ser None)
        new: Novos dados extraídos

    Returns:
        Dados mesclados
    """
    if existing is None:
        return new

    return ExtractedLeadData(
        name=new.name or existing.name,
        email=new.email or existing.email,
        phone=new.phone or existing.phone,
    )


def extract_from_history(messages: Sequence[str]) -> ExtractedLeadData:
    """Extrai dados de uma sequência de mensagens.

    Útil para reprocessar histórico e extrair dados perdidos.

    Args:
        messages: Lista de mensagens do usuário

    Returns:
        Dados acumulados de todas as mensagens
    """
    result: ExtractedLeadData | None = None

    for msg in messages:
        extracted = extract_lead_data(msg)
        result = merge_lead_data(result, extracted)

    return result or ExtractedLeadData()
