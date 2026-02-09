"""Runtime helpers para processamento do webhook WhatsApp."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.coordinators.whatsapp.inbound.handler import process_inbound_payload

logger = logging.getLogger(__name__)

_inbound_use_case: Any | None = None
_background_tasks: set[asyncio.Task[Any]] = set()


def get_inbound_use_case() -> Any:
    """Obtém o use case de processamento inbound (lazy-loading)."""
    global _inbound_use_case
    if _inbound_use_case is None:
        from app.bootstrap.dependencies import (
            create_async_dedupe_store,
            create_async_session_store,
            create_contact_card_extractor_service,
            create_contact_card_store,
            create_otto_agent_service,
            create_transcription_service,
        )
        from app.bootstrap.whatsapp_factory import (
            create_process_inbound_canonical,
            create_whatsapp_normalizer,
            create_whatsapp_outbound_sender,
        )

        _inbound_use_case = create_process_inbound_canonical(
            normalizer=create_whatsapp_normalizer(),
            session_store=create_async_session_store(),
            dedupe=create_async_dedupe_store(),
            otto_agent=create_otto_agent_service(),
            outbound_sender=create_whatsapp_outbound_sender(),
            contact_card_store=create_contact_card_store(),
            transcription_service=create_transcription_service(),
            contact_card_extractor=create_contact_card_extractor_service(),
        )
    return _inbound_use_case


async def process_inbound_payload_safe(
    *,
    payload: dict[str, Any],
    correlation_id: str,
    use_case: Any,
    tenant_id: str,
) -> None:
    """Executa processamento inbound sem propagar exceções para a rota."""
    try:
        await process_inbound_payload(
            payload=payload,
            correlation_id=correlation_id,
            use_case=use_case,
            tenant_id=tenant_id,
        )
    except Exception:
        logger.exception(
            "webhook_processing_failed",
            extra={
                "channel": "whatsapp",
                "correlation_id": correlation_id,
            },
        )


async def dispatch_inbound_processing(
    *,
    payload: dict[str, Any],
    correlation_id: str,
    settings: Any,
    tenant_id: str = "default",
) -> None:
    """Despacha processamento inline ou async conforme configuração."""
    use_case = get_inbound_use_case()
    if use_case is None:
        _log_use_case_unavailable(correlation_id)
        return

    processing_mode = (settings.webhook_processing_mode or "async").lower()
    if processing_mode == "inline":
        await process_inbound_payload_safe(
            payload=payload,
            correlation_id=correlation_id,
            use_case=use_case,
            tenant_id=tenant_id,
        )
        logger.info(
            "webhook_processing_completed",
            extra={
                "channel": "whatsapp",
                "correlation_id": correlation_id,
                "mode": "inline",
            },
        )
        return
    _schedule_async_processing(
        payload=payload,
        correlation_id=correlation_id,
        use_case=use_case,
        tenant_id=tenant_id,
    )


def _log_use_case_unavailable(correlation_id: str) -> None:
    logger.warning(
        "webhook_use_case_unavailable",
        extra={
            "channel": "whatsapp",
            "correlation_id": correlation_id,
            "reason": "ProcessInboundCanonicalUseCase could not be initialized",
        },
    )


def _schedule_async_processing(
    *,
    payload: dict[str, Any],
    correlation_id: str,
    use_case: Any,
    tenant_id: str,
) -> None:
    task = asyncio.create_task(
        process_inbound_payload_safe(
            payload=payload,
            correlation_id=correlation_id,
            use_case=use_case,
            tenant_id=tenant_id,
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    logger.info(
        "webhook_processing_scheduled",
        extra={"channel": "whatsapp", "correlation_id": correlation_id, "mode": "async"},
    )
