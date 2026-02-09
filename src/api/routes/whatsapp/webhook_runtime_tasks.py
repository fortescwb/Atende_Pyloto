"""Controle de tasks assíncronas para processamento do webhook WhatsApp."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable

logger = logging.getLogger(__name__)

_TASK_SEMAPHORE = asyncio.Semaphore(100)
_active_tasks: set[asyncio.Task[Any]] = set()


def schedule_processing_task(
    *,
    correlation_id: str,
    coroutine: Awaitable[None],
) -> int:
    """Agenda task assíncrona com limite de concorrência."""
    task = asyncio.create_task(_run_with_limit(coroutine))
    _active_tasks.add(task)
    task.add_done_callback(_on_processing_task_done)
    logger.info(
        "webhook_processing_scheduled",
        extra={
            "channel": "whatsapp",
            "correlation_id": correlation_id,
            "mode": "async",
            "active_tasks": len(_active_tasks),
        },
    )
    return len(_active_tasks)


async def _run_with_limit(coroutine: Awaitable[None]) -> None:
    async with _TASK_SEMAPHORE:
        await coroutine


def _on_processing_task_done(task: asyncio.Task[Any]) -> None:
    _active_tasks.discard(task)
    with contextlib.suppress(asyncio.CancelledError):
        exc = task.exception()
        if exc is not None:
            logger.error(
                "webhook_processing_task_failed",
                extra={
                    "channel": "whatsapp",
                    "error_type": type(exc).__name__,
                    "active_tasks": len(_active_tasks),
                },
            )


async def drain_processing_tasks(timeout_seconds: float = 30.0) -> None:
    """Aguarda tasks pendentes durante shutdown do processo."""
    if not _active_tasks:
        return

    pending_now = list(_active_tasks)
    logger.info(
        "webhook_processing_shutdown_wait",
        extra={
            "channel": "whatsapp",
            "pending_tasks": len(pending_now),
            "timeout_seconds": timeout_seconds,
        },
    )
    _, pending = await asyncio.wait(pending_now, timeout=timeout_seconds)
    if not pending:
        return

    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    logger.warning(
        "webhook_processing_shutdown_cancelled",
        extra={"channel": "whatsapp", "cancelled_tasks": len(pending)},
    )
