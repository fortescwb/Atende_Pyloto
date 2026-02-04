"""Extrator de JSON de respostas de LLM.

Extrai JSON de respostas brutas que podem conter markdown ou texto adicional.
Conforme REGRAS_E_PADROES.md § 4: arquivos ≤200 linhas.
"""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json_from_response(response: str) -> dict[str, Any] | None:
    """Extrai e valida JSON de resposta de LLM.

    Trata casos comuns:
    - Resposta envolvida em markdown code blocks
    - Whitespace extra
    - JSON embutido em texto

    Args:
        response: Resposta bruta da LLM

    Returns:
        Dict extraído do JSON ou None se não encontrado
    """
    if not response or not isinstance(response, str):
        return None

    text = response.strip()

    # Remover markdown code blocks se presentes
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    # Tentar parsear JSON direto
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # Tentar encontrar JSON no texto via regex
    json_pattern = r"\{[^{}]*\}"
    matches = re.findall(json_pattern, text, re.DOTALL)
    for match in matches:
        try:
            data = json.loads(match)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue

    return None
