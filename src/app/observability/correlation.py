"""Gerenciamento de correlation_id para rastreamento de requisições.

O correlation_id é propagado entre serviços e injetado em logs.
Usa ContextVar para ser thread/async-safe.

Uso:
    from app.observability import get_correlation_id, set_correlation_id

    # Em middleware/handler
    token = set_correlation_id(request.headers.get("x-correlation-id"))
    try:
        # processar request
    finally:
        reset_correlation_id(token)

    # Em qualquer lugar
    correlation_id = get_correlation_id()
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar, Token

# ContextVar para correlation_id (thread/async-safe)
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Retorna o correlation_id do contexto atual.

    Returns:
        correlation_id ou string vazia se não definido.
    """
    return _correlation_id.get()


def set_correlation_id(correlation_id: str | None = None) -> Token[str]:
    """Define o correlation_id no contexto atual.

    Args:
        correlation_id: ID a definir. Se None, gera um novo UUID.

    Returns:
        Token para reset posterior via reset_correlation_id().
    """
    value = correlation_id or str(uuid.uuid4())
    return _correlation_id.set(value)


def reset_correlation_id(token: Token[str]) -> None:
    """Restaura o correlation_id ao valor anterior.

    Args:
        token: Token retornado por set_correlation_id().
    """
    _correlation_id.reset(token)


def generate_correlation_id() -> str:
    """Gera um novo correlation_id (UUID v4).

    Returns:
        Novo UUID como string.
    """
    return str(uuid.uuid4())
