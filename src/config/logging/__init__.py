"""Configuração de logging estruturado.

Re-exporta funções e classes para configuração de logging JSON.

Uso:
    from config.logging import configure_logging, get_logger

    # Na inicialização (bootstrap)
    configure_logging(level="INFO", service_name="atende_pyloto")

    # Em qualquer módulo
    logger = get_logger(__name__)
    logger.info("Operação OK", extra={"latency_ms": 42})

Campos obrigatórios em todo log:
- correlation_id
- service
- level
- logger
- message
- asctime

Conforme REGRAS_E_PADROES.md: logs estruturados, sem PII.
"""

from config.logging.config import configure_logging, get_logger, log_fallback
from config.logging.filters import CorrelationIdFilter
from config.logging.formatters import (
    FIELD_RENAME_MAP,
    REQUIRED_LOG_FIELDS,
    create_json_formatter,
)

__all__ = [
    "FIELD_RENAME_MAP",
    "REQUIRED_LOG_FIELDS",
    # Filters
    "CorrelationIdFilter",
    # Configuração principal
    "configure_logging",
    # Formatters
    "create_json_formatter",
    "get_logger",
    "log_fallback",
]
