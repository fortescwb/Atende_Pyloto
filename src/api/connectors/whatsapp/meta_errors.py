"""Erros e helpers de parsing para API Meta/WhatsApp."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WhatsAppApiError:
    """Erro retornado pela API Meta/WhatsApp."""

    error_type: str
    error_code: int
    error_message: str
    is_permanent: bool  # True se erro não é retentável


def is_permanent_error(error_code: int, error_type: str) -> bool:
    """Classifica erro como permanente ou transitório.

    Erros permanentes: 400, 401, 403, 404, 413
    Erros transitórios: 429 (rate limit), 500+ (server errors)
    """
    permanent_codes = {400, 401, 403, 404, 413}
    if error_code in permanent_codes:
        return True

    permanent_types = {"OAuthException", "InvalidRequest"}
    return error_type in permanent_types


def parse_meta_error(response_data: dict[str, Any]) -> WhatsAppApiError | None:
    """Extrai informações de erro do response da Meta.

    Args:
        response_data: Dict do response JSON

    Returns:
        WhatsAppApiError se houver erro, None se sucesso
    """
    error_obj = response_data.get("error")
    if not error_obj or not isinstance(error_obj, dict):
        return None

    error_type = error_obj.get("type", "unknown")
    error_code = error_obj.get("code", 0)
    error_message = error_obj.get("message", "Erro desconhecido")

    return WhatsAppApiError(
        error_type=error_type,
        error_code=error_code,
        error_message=error_message,
        is_permanent=is_permanent_error(error_code, error_type),
    )
