"""Observabilidade — logs estruturados, tracing, métricas.

Re-exporta funções de correlation_id para uso em toda a aplicação.

Uso:
    from app.observability import get_correlation_id, set_correlation_id
"""

from app.observability.correlation import (
    generate_correlation_id,
    get_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)

__all__ = [
    "generate_correlation_id",
    "get_correlation_id",
    "reset_correlation_id",
    "set_correlation_id",
]
