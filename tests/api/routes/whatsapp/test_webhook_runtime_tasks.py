"""Testes para controle de tasks assíncronas do webhook."""

from __future__ import annotations

import asyncio

import pytest

from api.routes.whatsapp import webhook_runtime_tasks


async def _wait_until_tasks_empty(timeout: float = 1.0) -> None:
    start = asyncio.get_running_loop().time()
    while webhook_runtime_tasks._active_tasks:
        if asyncio.get_running_loop().time() - start > timeout:
            break
        await asyncio.sleep(0.01)


@pytest.fixture(autouse=True)
async def _cleanup_active_tasks() -> None:
    for task in list(webhook_runtime_tasks._active_tasks):
        task.cancel()
    if webhook_runtime_tasks._active_tasks:
        await asyncio.gather(
            *list(webhook_runtime_tasks._active_tasks),
            return_exceptions=True,
        )
    webhook_runtime_tasks._active_tasks.clear()
    yield
    for task in list(webhook_runtime_tasks._active_tasks):
        task.cancel()
    if webhook_runtime_tasks._active_tasks:
        await asyncio.gather(
            *list(webhook_runtime_tasks._active_tasks),
            return_exceptions=True,
        )
    webhook_runtime_tasks._active_tasks.clear()


@pytest.mark.asyncio
async def test_schedule_processing_task_runs_coroutine_and_cleans_active_set() -> None:
    event = asyncio.Event()

    async def _work() -> None:
        event.set()

    active = webhook_runtime_tasks.schedule_processing_task(
        correlation_id="corr-1",
        coroutine=_work(),
    )

    assert active == 1
    await asyncio.wait_for(event.wait(), timeout=1.0)
    await _wait_until_tasks_empty()
    assert len(webhook_runtime_tasks._active_tasks) == 0


@pytest.mark.asyncio
async def test_schedule_processing_task_logs_failure(caplog: pytest.LogCaptureFixture) -> None:
    async def _boom() -> None:
        raise RuntimeError("boom")

    with caplog.at_level("ERROR"):
        webhook_runtime_tasks.schedule_processing_task(
            correlation_id="corr-2",
            coroutine=_boom(),
        )
        await _wait_until_tasks_empty()

    assert "webhook_processing_task_failed" in caplog.text


@pytest.mark.asyncio
async def test_drain_processing_tasks_returns_immediately_when_empty() -> None:
    await webhook_runtime_tasks.drain_processing_tasks(timeout_seconds=0.01)
    assert len(webhook_runtime_tasks._active_tasks) == 0


@pytest.mark.asyncio
async def test_drain_processing_tasks_waits_and_finishes_without_cancel() -> None:
    event = asyncio.Event()

    async def _short_work() -> None:
        await asyncio.sleep(0.02)
        event.set()

    webhook_runtime_tasks.schedule_processing_task(
        correlation_id="corr-3",
        coroutine=_short_work(),
    )

    await webhook_runtime_tasks.drain_processing_tasks(timeout_seconds=0.5)

    assert event.is_set() is True
    assert len(webhook_runtime_tasks._active_tasks) == 0


@pytest.mark.asyncio
async def test_drain_processing_tasks_cancels_pending_tasks(
    caplog: pytest.LogCaptureFixture,
) -> None:
    gate = asyncio.Event()

    async def _pending_work() -> None:
        await gate.wait()

    webhook_runtime_tasks.schedule_processing_task(
        correlation_id="corr-4",
        coroutine=_pending_work(),
    )
    await asyncio.sleep(0)

    with caplog.at_level("WARNING"):
        await webhook_runtime_tasks.drain_processing_tasks(timeout_seconds=0.01)

    assert "webhook_processing_shutdown_cancelled" in caplog.text
    assert len(webhook_runtime_tasks._active_tasks) == 0
