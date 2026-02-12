"""Casos de erro complementares do client de Google Calendar."""

from __future__ import annotations

from typing import Any

import pytest

from .test_google_calendar_client import _build_client, _build_http_error


@pytest.mark.asyncio
async def test_cancel_event_returns_false_on_404(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client(monkeypatch)
    error = _build_http_error(404)

    def _raise_http_error(event_id: str) -> None:
        _ = event_id
        raise error

    monkeypatch.setattr(client, "_delete_event_sync", _raise_http_error)

    result = await client.cancel_event("evt-missing")

    assert result is False


@pytest.mark.asyncio
async def test_get_event_returns_none_on_404(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client(monkeypatch)
    error = _build_http_error(404)

    def _raise_http_error(event_id: str) -> dict[str, Any]:
        _ = event_id
        raise error

    monkeypatch.setattr(client, "_get_event_sync", _raise_http_error)

    result = await client.get_event("evt-missing")

    assert result is None
