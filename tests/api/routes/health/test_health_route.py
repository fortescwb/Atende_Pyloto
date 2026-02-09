"""Testes dos endpoints de health e readiness."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from api.routes.health.router import readiness_check


def _build_request_with_state(state: SimpleNamespace) -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "path": "/ready",
        "raw_path": b"/ready",
        "query_string": b"",
        "headers": [],
        "app": SimpleNamespace(state=state),
    }

    async def _receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, _receive)


@pytest.mark.asyncio
async def test_readiness_returns_not_ready_without_dependencies() -> None:
    request = _build_request_with_state(
        SimpleNamespace(redis_client=None, firestore_client=None, openai_client=None)
    )

    response = await readiness_check(request)
    payload = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 503
    assert payload["status"] == "not_ready"
    assert payload["checks"]["redis"]["status"] == "failed"
    assert payload["checks"]["firestore"]["status"] == "failed"
    assert payload["checks"]["openai"]["status"] == "degraded"


@pytest.mark.asyncio
async def test_readiness_returns_ready_when_critical_dependencies_are_ok() -> None:
    redis_client = MagicMock()
    redis_client.ping = AsyncMock(return_value=True)

    firestore_doc = SimpleNamespace(exists=True)
    firestore_client = MagicMock()
    firestore_client.collection.return_value.document.return_value.get.return_value = firestore_doc

    openai_client = MagicMock()
    openai_client.models = MagicMock()
    openai_client.models.list = AsyncMock(return_value=[])

    request = _build_request_with_state(
        SimpleNamespace(
            redis_client=redis_client,
            firestore_client=firestore_client,
            openai_client=openai_client,
        )
    )

    response = await readiness_check(request)
    payload = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 200
    assert payload["status"] == "ready"
    assert payload["checks"]["redis"]["status"] == "ok"
    assert payload["checks"]["firestore"]["status"] == "ok"
    assert payload["checks"]["openai"]["status"] == "ok"
