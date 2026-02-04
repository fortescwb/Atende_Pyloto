"""Testes abrangentes para config.logging.

Cobre: configure_logging, get_logger, log_fallback,
CorrelationIdFilter, create_json_formatter.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from config.logging import (
    FIELD_RENAME_MAP,
    REQUIRED_LOG_FIELDS,
    CorrelationIdFilter,
    configure_logging,
    create_json_formatter,
    get_logger,
    log_fallback,
)
from config.logging.config import DEFAULT_SERVICE_NAME, VALID_LOG_LEVELS


class TestConfigureLogging:
    """Testes para configure_logging."""

    def test_configure_logging_default_level(self) -> None:
        """Configura logging com nível padrão INFO."""
        configure_logging()
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_configure_logging_debug_level(self) -> None:
        """Configura logging com nível DEBUG."""
        configure_logging(level="DEBUG")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_configure_logging_warning_level(self) -> None:
        """Configura logging com nível WARNING."""
        configure_logging(level="warning")  # case insensitive
        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_configure_logging_error_level(self) -> None:
        """Configura logging com nível ERROR."""
        configure_logging(level="ERROR")
        root = logging.getLogger()
        assert root.level == logging.ERROR

    def test_configure_logging_critical_level(self) -> None:
        """Configura logging com nível CRITICAL."""
        configure_logging(level="CRITICAL")
        root = logging.getLogger()
        assert root.level == logging.CRITICAL

    def test_configure_logging_invalid_level_raises(self) -> None:
        """Nível inválido levanta ValueError."""
        with pytest.raises(ValueError, match="Nível de log inválido"):
            configure_logging(level="INVALID")

    def test_configure_logging_replaces_handlers(self) -> None:
        """Configure_logging substitui handlers existentes."""
        root = logging.getLogger()
        root.handlers = [logging.NullHandler(), logging.NullHandler()]
        configure_logging()
        assert len(root.handlers) == 1

    def test_configure_logging_with_correlation_id_getter(self) -> None:
        """Aceita correlation_id_getter customizado."""
        getter = lambda: "custom-corr-id"  # noqa: E731
        configure_logging(correlation_id_getter=getter)
        root = logging.getLogger()
        assert len(root.handlers) == 1
        # Verifica que o filter foi adicionado
        handler = root.handlers[0]
        filters = handler.filters
        assert any(isinstance(f, CorrelationIdFilter) for f in filters)

    def test_valid_log_levels_constant(self) -> None:
        """VALID_LOG_LEVELS contém os níveis esperados."""
        assert {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"} == VALID_LOG_LEVELS

    def test_default_service_name_constant(self) -> None:
        """DEFAULT_SERVICE_NAME está definido."""
        assert DEFAULT_SERVICE_NAME == "atende_pyloto"


class TestGetLogger:
    """Testes para get_logger."""

    def test_get_logger_returns_logger(self) -> None:
        """Retorna um logger para o nome especificado."""
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_get_logger_same_name_returns_same_instance(self) -> None:
        """Mesmo nome retorna mesma instância."""
        logger1 = get_logger("same.module")
        logger2 = get_logger("same.module")
        assert logger1 is logger2


class TestLogFallback:
    """Testes para log_fallback."""

    def test_log_fallback_basic(self) -> None:
        """Log fallback básico com componente."""
        logger = MagicMock(spec=logging.Logger)
        log_fallback(logger, "response_generation")
        logger.info.assert_called_once()
        call_args = logger.info.call_args
        # Verifica formato lazy: primeiro arg é template, segundo é o componente
        assert call_args[0][0] == "Fallback applied for %s"
        assert call_args[0][1] == "response_generation"
        extra = call_args[1]["extra"]
        assert extra["fallback_used"] is True
        assert extra["component"] == "response_generation"

    def test_log_fallback_with_reason(self) -> None:
        """Log fallback com reason."""
        logger = MagicMock(spec=logging.Logger)
        log_fallback(logger, "ai_timeout", reason="api_timeout")
        extra = logger.info.call_args[1]["extra"]
        assert extra["reason"] == "api_timeout"

    def test_log_fallback_with_elapsed_ms(self) -> None:
        """Log fallback com elapsed_ms."""
        logger = MagicMock(spec=logging.Logger)
        log_fallback(logger, "parser", elapsed_ms=123.45)
        extra = logger.info.call_args[1]["extra"]
        assert extra["elapsed_ms"] == 123.45

    def test_log_fallback_with_all_params(self) -> None:
        """Log fallback com todos os parâmetros."""
        logger = MagicMock(spec=logging.Logger)
        log_fallback(logger, "component", reason="timeout", elapsed_ms=5000.0)
        extra = logger.info.call_args[1]["extra"]
        assert extra["fallback_used"] is True
        assert extra["component"] == "component"
        assert extra["reason"] == "timeout"
        assert extra["elapsed_ms"] == 5000.0

    def test_log_fallback_without_optional_params(self) -> None:
        """Log fallback sem reason e elapsed_ms."""
        logger = MagicMock(spec=logging.Logger)
        log_fallback(logger, "test_component")
        extra = logger.info.call_args[1]["extra"]
        assert "reason" not in extra
        assert "elapsed_ms" not in extra


class TestCorrelationIdFilter:
    """Testes para CorrelationIdFilter."""

    def test_filter_adds_correlation_id_from_getter(self) -> None:
        """Filter adiciona correlation_id do getter."""
        getter = lambda: "corr-123"  # noqa: E731
        filter_ = CorrelationIdFilter("my_service", getter)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="message",
            args=(),
            exc_info=None,
        )
        result = filter_.filter(record)
        assert result is True
        assert record.correlation_id == "corr-123"
        assert record.service == "my_service"

    def test_filter_preserves_explicit_correlation_id(self) -> None:
        """Filter preserva correlation_id passado via extra."""
        getter = lambda: "from-getter"  # noqa: E731
        filter_ = CorrelationIdFilter("svc", getter)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="msg",
            args=(),
            exc_info=None,
        )
        record.correlation_id = "explicit-id"
        filter_.filter(record)
        assert record.correlation_id == "explicit-id"

    def test_filter_uses_empty_string_when_no_getter(self) -> None:
        """Filter usa string vazia quando não há getter."""
        filter_ = CorrelationIdFilter("service_name", None)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="msg",
            args=(),
            exc_info=None,
        )
        filter_.filter(record)
        assert record.correlation_id == ""
        assert record.service == "service_name"

    def test_filter_always_returns_true(self) -> None:
        """Filter sempre retorna True (não filtra, apenas enriquece)."""
        filter_ = CorrelationIdFilter("svc")
        record = logging.LogRecord(
            name="x",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )
        assert filter_.filter(record) is True


class TestCreateJsonFormatter:
    """Testes para create_json_formatter e constantes."""

    def test_required_log_fields_is_frozenset(self) -> None:
        """REQUIRED_LOG_FIELDS é frozenset."""
        assert isinstance(REQUIRED_LOG_FIELDS, frozenset)

    def test_required_log_fields_content(self) -> None:
        """REQUIRED_LOG_FIELDS contém campos obrigatórios."""
        expected = {"asctime", "levelname", "name", "message", "correlation_id", "service"}
        assert expected == REQUIRED_LOG_FIELDS

    def test_field_rename_map_content(self) -> None:
        """FIELD_RENAME_MAP mapeia campos corretamente."""
        assert FIELD_RENAME_MAP == {"levelname": "level", "name": "logger"}

    def test_create_json_formatter_returns_formatter(self) -> None:
        """create_json_formatter retorna JsonFormatter."""
        from pythonjsonlogger.json import JsonFormatter

        formatter = create_json_formatter()
        assert isinstance(formatter, JsonFormatter)

    def test_json_formatter_formats_record(self) -> None:
        """JsonFormatter formata record como JSON."""
        formatter = create_json_formatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.correlation_id = "abc-123"
        record.service = "test_service"
        output = formatter.format(record)
        assert "Test message" in output
        assert "test.logger" in output or "logger" in output
        assert "INFO" in output or "level" in output


class TestLoggingIntegration:
    """Testes de integração do sistema de logging."""

    def test_full_logging_flow(self) -> None:
        """Fluxo completo: configure, get_logger, log."""
        configure_logging(
            level="DEBUG",
            service_name="integration_test",
            correlation_id_getter=lambda: "int-test-001",
        )
        logger = get_logger("integration.test")
        # Não deve levantar exceção
        logger.debug("Debug message", extra={"custom_field": "value"})
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

    def test_logger_with_extra_fields(self) -> None:
        """Logger aceita extra fields customizados."""
        configure_logging(level="INFO", service_name="extra_test")
        logger = get_logger("extra.fields")
        # Não deve levantar exceção
        logger.info(
            "With extras",
            extra={
                "latency_ms": 42,
                "event_type": "test",
                "tenant_id": "t123",
            },
        )
