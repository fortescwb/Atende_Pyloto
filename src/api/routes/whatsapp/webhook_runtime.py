"""Runtime helpers para processamento do webhook WhatsApp."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from api.routes.whatsapp.webhook_runtime_tasks import (
    drain_processing_tasks,
    schedule_processing_task,
)
from app.coordinators.whatsapp.inbound.handler import process_inbound_payload
from app.protocols.validator import ValidationError as OutboundValidationError
from utils.errors import FirestoreUnavailableError, RedisConnectionError

logger = logging.getLogger(__name__)

_inbound_use_case: Any | None = None


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
    """Executa processamento inbound com classificação explícita de erros."""
    try:
        await process_inbound_payload(
            payload=payload,
            correlation_id=correlation_id,
            use_case=use_case,
            tenant_id=tenant_id,
        )
    except Exception as exc:
        if _is_validation_error(exc):
            logger.warning(
                "webhook_processing_validation_failed",
                extra={
                    "channel": "whatsapp",
                    "correlation_id": correlation_id,
                    "error_type": type(exc).__name__,
                },
            )
            return
        if _is_infrastructure_error(exc):
            logger.error(
                "webhook_processing_infra_failed",
                extra={
                    "channel": "whatsapp",
                    "correlation_id": correlation_id,
                    "error_type": type(exc).__name__,
                },
            )
            raise
        logger.exception(
            "webhook_processing_failed",
            extra={
                "channel": "whatsapp",
                "correlation_id": correlation_id,
            },
        )
        raise


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
    schedule_processing_task(
        correlation_id=correlation_id,
        coroutine=process_inbound_payload_safe(
            payload=payload,
            correlation_id=correlation_id,
            use_case=use_case,
            tenant_id=tenant_id,
        )
    )


async def drain_background_tasks(timeout_seconds: float = 30.0) -> None:
    """Aguarda tasks async pendentes durante shutdown do processo."""
    await drain_processing_tasks(timeout_seconds=timeout_seconds)


def _is_validation_error(exc: Exception) -> bool:
    return isinstance(exc, (ValueError, PydanticValidationError, OutboundValidationError))


def _is_infrastructure_error(exc: Exception) -> bool:
    if isinstance(exc, (RedisConnectionError, FirestoreUnavailableError)):
        return True
    module_name = type(exc).__module__
    return module_name.startswith(("redis.", "google.api_core."))
