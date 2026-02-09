"""Testes para helpers runtime do webhook WhatsApp."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from api.routes.whatsapp import webhook_runtime


@pytest.mark.asyncio
async def test_dispatch_inbound_processing_inline_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    use_case = object()
    captured: dict[str, object] = {}

    monkeypatch.setattr(webhook_runtime, "get_inbound_use_case", lambda: use_case)

    async def _fake_process_inbound_payload_safe(
        *,
        payload: dict[str, object],
        correlation_id: str,
        use_case: object,
        tenant_id: str,
    ) -> None:
        captured["payload"] = payload
        captured["correlation_id"] = correlation_id
        captured["use_case"] = use_case
        captured["tenant_id"] = tenant_id

    monkeypatch.setattr(
        webhook_runtime,
        "process_inbound_payload_safe",
        _fake_process_inbound_payload_safe,
    )

    await webhook_runtime.dispatch_inbound_processing(
        payload={"entry": []},
        correlation_id="corr-inline",
        settings=SimpleNamespace(webhook_processing_mode="inline"),
        tenant_id="tenant-a",
    )

    assert captured == {
        "payload": {"entry": []},
        "correlation_id": "corr-inline",
        "use_case": use_case,
        "tenant_id": "tenant-a",
    }


@pytest.mark.asyncio
async def test_dispatch_inbound_processing_async_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    use_case = object()
    captured: dict[str, object] = {}

    monkeypatch.setattr(webhook_runtime, "get_inbound_use_case", lambda: use_case)

    def _fake_schedule_async_processing(
        *,
        payload: dict[str, object],
        correlation_id: str,
        use_case: object,
        tenant_id: str,
    ) -> None:
        captured["payload"] = payload
        captured["correlation_id"] = correlation_id
        captured["use_case"] = use_case
        captured["tenant_id"] = tenant_id

    monkeypatch.setattr(
        webhook_runtime,
        "_schedule_async_processing",
        _fake_schedule_async_processing,
    )

    await webhook_runtime.dispatch_inbound_processing(
        payload={"entry": [{"id": "1"}]},
        correlation_id="corr-async",
        settings=SimpleNamespace(webhook_processing_mode="async"),
        tenant_id="tenant-b",
    )

    assert captured == {
        "payload": {"entry": [{"id": "1"}]},
        "correlation_id": "corr-async",
        "use_case": use_case,
        "tenant_id": "tenant-b",
    }


@pytest.mark.asyncio
async def test_dispatch_inbound_processing_without_use_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    monkeypatch.setattr(webhook_runtime, "get_inbound_use_case", lambda: None)
    monkeypatch.setattr(
        webhook_runtime,
        "_log_use_case_unavailable",
        lambda correlation_id: captured.setdefault("correlation_id", correlation_id),
    )

    await webhook_runtime.dispatch_inbound_processing(
        payload={},
        correlation_id="corr-missing",
        settings=SimpleNamespace(webhook_processing_mode="inline"),
    )

    assert captured["correlation_id"] == "corr-missing"


@pytest.mark.asyncio
async def test_process_inbound_payload_safe_raises_unexpected_exceptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _raise(
        *,
        payload: dict[str, object],
        correlation_id: str,
        use_case: object,
        tenant_id: str,
    ) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(webhook_runtime, "process_inbound_payload", _raise)

    with pytest.raises(RuntimeError, match="boom"):
        await webhook_runtime.process_inbound_payload_safe(
            payload={"entry": []},
            correlation_id="corr-safe",
            use_case=object(),
            tenant_id="tenant-c",
        )


@pytest.mark.asyncio
async def test_process_inbound_payload_safe_swallows_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _raise_validation(
        *,
        payload: dict[str, object],
        correlation_id: str,
        use_case: object,
        tenant_id: str,
    ) -> None:
        raise ValueError("invalid payload")

    monkeypatch.setattr(webhook_runtime, "process_inbound_payload", _raise_validation)

    await webhook_runtime.process_inbound_payload_safe(
        payload={"entry": []},
        correlation_id="corr-validation",
        use_case=object(),
        tenant_id="tenant-c",
    )
