"""Helpers de logging para API Meta/WhatsApp (sem PII)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .meta_errors import WhatsAppApiError

logger = logging.getLogger(__name__)


def log_meta_error(
    meta_error: WhatsAppApiError,
    method: str,
    endpoint: str,
) -> None:
    """Loga erro da Meta sem expor dados sensíveis."""
    logger.warning(
        "Erro da API Meta/WhatsApp",
        extra={
            "method": method,
            "endpoint": endpoint,
            "error_type": meta_error.error_type,
            "error_code": meta_error.error_code,
            "is_permanent": meta_error.is_permanent,
        },
    )


def log_success(
    method: str,
    endpoint: str,
    status_code: int,
) -> None:
    """Loga sucesso sem expor dados sensíveis."""
    logger.debug(
        "Envio WhatsApp bem-sucedido",
        extra={
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
        },
    )
