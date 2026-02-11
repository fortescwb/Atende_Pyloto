"""Registro de métricas via structured logging.

P1-2: Métricas básicas para observabilidade do sistema Otto.

As métricas são registradas como logs estruturados e podem ser agregadas
posteriormente por sistemas como BigQuery, CloudWatch Insights, etc.

Métricas suportadas:
- Latência: histogram de tempos de execução por componente/operação
- Confidence: gauge de confiança média das decisões LLM
- Handoff: counter de escalações para humano com motivo

Uso:
    from app.observability.metrics import record_latency, record_confidence, record_handoff

    # Latência
    start = time.perf_counter()
    # ... operação ...
    latency_ms = (time.perf_counter() - start) * 1000
    record_latency("otto_agent", "decide", latency_ms, correlation_id)

    # Confidence
    record_confidence("otto_agent", "decision", decision.confidence, correlation_id)

    # Handoff
    record_handoff("low_confidence", correlation_id)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def record_latency(
    component: str,
    operation: str,
    latency_ms: float,
    correlation_id: str | None = None,
) -> None:
    """Registra latência de operação.

    Args:
        component: Nome do componente (ex: "otto_agent", "micro_agents")
        operation: Nome da operação (ex: "decide", "build_prompt")
        latency_ms: Latência em milissegundos
        correlation_id: ID de correlação para rastreamento
    """
    logger.info(
        "metric_latency",
        extra={
            "metric_type": "latency",
            "component": component,
            "operation": operation,
            "latency_ms": round(latency_ms, 2),
            "correlation_id": correlation_id,
        },
    )


def record_confidence(
    component: str,
    operation: str,
    confidence: float,
    correlation_id: str | None = None,
) -> None:
    """Registra métrica de confidence.

    Args:
        component: Nome do componente (ex: "otto_agent", "validation")
        operation: Nome da operação (ex: "decision", "gate_check")
        confidence: Valor de confidence (0.0-1.0)
        correlation_id: ID de correlação para rastreamento
    """
    logger.info(
        "metric_confidence",
        extra={
            "metric_type": "confidence",
            "component": component,
            "operation": operation,
            "confidence": round(confidence, 3),
            "correlation_id": correlation_id,
        },
    )


def record_handoff(
    reason: str,
    correlation_id: str | None = None,
    metadata: dict[str, str | float | int] | None = None,
) -> None:
    """Registra escalação para humano.

    Args:
        reason: Motivo do handoff (ex: "low_confidence", "explicit_request", "validation_failed")
        correlation_id: ID de correlação para rastreamento
        metadata: Metadados adicionais opcionais
    """
    extra = {
        "metric_type": "handoff",
        "component": "handoff",
        "reason": reason,
        "correlation_id": correlation_id,
    }
    if metadata:
        extra.update(metadata)

    logger.info(
        "metric_handoff",
        extra=extra,
    )


def record_token_usage(
    component: str,
    operation: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    correlation_id: str | None = None,
) -> None:
    """Registra uso de tokens (custo).

    Args:
        component: Nome do componente (ex: "otto_agent", "extraction_agent")
        operation: Nome da operação (ex: "decide", "extract")
        prompt_tokens: Tokens no prompt
        completion_tokens: Tokens na resposta
        total_tokens: Total de tokens
        correlation_id: ID de correlação para rastreamento
    """
    logger.info(
        "metric_token_usage",
        extra={
            "metric_type": "token_usage",
            "component": component,
            "operation": operation,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "correlation_id": correlation_id,
        },
    )
