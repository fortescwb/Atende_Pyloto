"""Processamento inbound: normaliza, orquestra e enfileira outbound.

Utiliza ProcessInboundCanonicalUseCase (pipeline Otto + utilitários).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.use_cases.whatsapp.process_inbound_canonical import (
        InboundProcessingResult,
        ProcessInboundCanonicalUseCase,
    )

logger = logging.getLogger(__name__)


async def process_inbound_payload(
    payload: dict[str, Any],
    correlation_id: str,
    use_case: ProcessInboundCanonicalUseCase,
    tenant_id: str = "",
) -> InboundProcessingResult:
    """Processa payload inbound via pipeline canônico.

    Sem logs com PII. As mensagens são normalizadas e processadas uma a uma.

    Args:
        payload: Payload do webhook
        correlation_id: ID de correlação para rastreamento
        use_case: Use case canônico injetado
        tenant_id: ID do tenant (multi-tenant)

    Returns:
        InboundProcessingResult com métricas de processamento
    """
    result = await use_case.execute(
        payload=payload,
        correlation_id=correlation_id,
        tenant_id=tenant_id,
    )

    logger.info(
        "inbound_processed",
        extra={
            "session_id": result.session_id,
            "processed": result.processed,
            "skipped": result.skipped,
            "sent": result.sent,
            "final_state": result.final_state,
        },
    )

    return result
