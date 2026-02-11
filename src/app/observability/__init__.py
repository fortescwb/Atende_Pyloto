"""Observabilidade — logs estruturados, tracing, métricas.

Re-exporta funções de correlation_id e métricas para uso em toda a aplicação.

Uso:
    from app.observability import get_correlation_id, set_correlation_id
    from app.observability import record_latency, record_confidence, record_handoff
"""

from app.observability.correlation import (
    generate_correlation_id,
    get_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)
from app.observability.metrics import (
    record_confidence,
    record_handoff,
    record_latency,
    record_token_usage,
)

__all__ = [
    "generate_correlation_id",
    "get_correlation_id",
    "record_confidence",
    "record_handoff",
    "record_latency",
    "record_token_usage",
    "reset_correlation_id",
    "set_correlation_id",
]
