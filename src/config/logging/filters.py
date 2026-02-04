"""Filters de logging para injeção de contexto.

Filters são responsáveis por adicionar campos contextuais
aos logs sem que o chamador precise informá-los manualmente.

Campos injetados:
- correlation_id: ID de rastreamento da requisição
- service: Nome do serviço (ex: atende_pyloto)

Conforme REGRAS_E_PADROES.md: logs estruturados, sem PII.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class CorrelationIdFilter(logging.Filter):
    """Injeta correlation_id e service em cada record de log.

    Importante: nunca adicionar payloads brutos ou PII nos logs.

    Args:
        service_name: Nome do serviço para identificação nos logs.
        correlation_id_getter: Função que retorna o correlation_id atual.
            Se não fornecida, usa string vazia como fallback.
    """

    def __init__(
        self,
        service_name: str,
        correlation_id_getter: Callable[[], str] | None = None,
    ) -> None:
        """Inicializa o filter.

        Args:
            service_name: Nome do serviço (ex: "atende_pyloto").
            correlation_id_getter: Função para obter correlation_id do contexto.
        """
        super().__init__()
        self._service_name = service_name
        self._get_correlation_id = correlation_id_getter or (lambda: "")

    def filter(self, record: logging.LogRecord) -> bool:
        """Adiciona correlation_id e service ao record.

        Se correlation_id já foi passado via `extra`, preserva o valor.

        Args:
            record: LogRecord a ser enriquecido.

        Returns:
            True sempre (não filtra, apenas enriquece).
        """
        # Preservar correlation_id passado explicitamente via `extra`
        existing = getattr(record, "correlation_id", None)
        record.correlation_id = existing if existing else self._get_correlation_id()
        record.service = self._service_name
        return True
