"""Configuração centralizada de logging.

Funções para configurar logging estruturado JSON com:
- Campos obrigatórios (correlation_id, service, level, logger, message)
- Formatação padronizada
- Níveis configuráveis por ambiente

Uso:
    from config.logging import configure_logging, get_logger

    # Na inicialização do serviço (app/bootstrap/)
    configure_logging(level="INFO", service_name="atende_pyloto")

    # Em qualquer módulo
    logger = get_logger(__name__)
    logger.info("Operação concluída", extra={"latency_ms": 42})

Conforme REGRAS_E_PADROES.md: logs estruturados, sem PII.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from config.logging.filters import CorrelationIdFilter
from config.logging.formatters import create_json_formatter

if TYPE_CHECKING:
    from collections.abc import Callable

# Níveis de log válidos
VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})

# Nome padrão do serviço
DEFAULT_SERVICE_NAME = "atende_pyloto"


def configure_logging(
    level: str = "INFO",
    service_name: str = DEFAULT_SERVICE_NAME,
    correlation_id_getter: Callable[[], str] | None = None,
) -> None:
    """Configura logging JSON estruturado para o serviço.

    Deve ser chamada uma vez na inicialização do serviço (app/bootstrap/).

    Args:
        level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        service_name: Nome do serviço para identificação nos logs.
        correlation_id_getter: Função opcional que retorna o correlation_id
            do contexto atual (ex: de ContextVar).

    Raises:
        ValueError: Se o nível de log for inválido.

    Exemplo:
        configure_logging(
            level="INFO",
            service_name="atende_pyloto",
            correlation_id_getter=get_correlation_id,  # de app/observability
        )
    """
    level_upper = level.upper()
    if level_upper not in VALID_LOG_LEVELS:
        raise ValueError(
            f"Nível de log inválido: {level}. "
            f"Válidos: {', '.join(sorted(VALID_LOG_LEVELS))}"
        )

    formatter = create_json_formatter()

    handler = logging.StreamHandler()
    handler.setLevel(level_upper)
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter(service_name, correlation_id_getter))

    root = logging.getLogger()
    root.setLevel(level_upper)
    # Substituir handlers existentes para evitar duplicação
    root.handlers = [handler]


def get_logger(name: str) -> logging.Logger:
    """Retorna logger para o módulo especificado.

    O filter injeta automaticamente service e correlation_id.

    Args:
        name: Nome do logger (geralmente __name__).

    Returns:
        Logger configurado.

    Exemplo:
        logger = get_logger(__name__)
        logger.info("Mensagem", extra={"event_id": "abc123"})
    """
    return logging.getLogger(name)


def log_fallback(
    logger: logging.Logger,
    component: str,
    reason: str | None = None,
    elapsed_ms: float | None = None,
) -> None:
    """Log observável de fallback usado (sem PII).

    Útil para registrar quando um fallback determinístico
    foi acionado (ex: timeout de IA, parse error).

    Args:
        logger: Logger instance.
        component: Nome do componente (ex: "response_generation").
        reason: Razão do fallback (ex: "timeout") — sem PII.
        elapsed_ms: Tempo decorrido em ms (quando aplicável).

    Exemplo:
        log_fallback(
            logger,
            "response_generation",
            reason="api_timeout",
            elapsed_ms=5230.5,
        )
    """
    extra: dict[str, object] = {
        "fallback_used": True,
        "component": component,
    }
    if reason:
        extra["reason"] = reason
    if elapsed_ms is not None:
        extra["elapsed_ms"] = elapsed_ms

    logger.info(
        "Fallback applied for %s",
        component,
        extra=extra,
    )
