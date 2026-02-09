"""Testes para endpoints da rota de webhook WhatsApp."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from starlette.requests import Request

from api.connectors.whatsapp.signature import SignatureResult
from api.connectors.whatsapp.webhook.receive import InvalidJsonError, InvalidSignatureError
from api.routes.whatsapp import webhook


def _build_request(
    *,
    method: str,
    query_string: str = "",
    body: bytes = b"",
    headers: dict[str, str] | None = None,
) -> Request:
    header_items = headers or {}
    raw_headers = [(k.lower().encode("utf-8"), v.encode("utf-8")) for k, v in header_items.items()]
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": "/",
        "raw_path": b"/",
        "query_string": query_string.encode("utf-8"),
        "headers": raw_headers,
    }
    sent = False

    async def _receive() -> dict[str, object]:
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(scope, _receive)


@pytest.mark.asyncio
async def test_verify_webhook_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        webhook,
        "get_whatsapp_settings",
        lambda: SimpleNamespace(verify_token="token"),
    )

    request = _build_request(
        method="GET",
        query_string="hub.mode=subscribe&hub.verify_token=token&hub.challenge=abc",
    )
    response = await webhook.verify_webhook(request)

    assert response.status_code == 200
    assert response.body == b"abc"


@pytest.mark.asyncio
async def test_verify_webhook_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        webhook,
        "get_whatsapp_settings",
        lambda: SimpleNamespace(verify_token="token"),
    )

    request = _build_request(
        method="GET",
        query_string="hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=abc",
    )
    response = await webhook.verify_webhook(request)

    assert response.status_code == 403
    assert response.body == b"Forbidden"


@pytest.mark.asyncio
async def test_receive_webhook_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        webhook,
        "get_whatsapp_settings",
        lambda: SimpleNamespace(webhook_secret="secret", webhook_processing_mode="inline"),
    )
    monkeypatch.setattr(
        webhook,
        "parse_webhook_request",
        lambda raw_body, headers, secret: (
            {"entry": []},
            SignatureResult(valid=True, skipped=False),
        ),
    )

    async def _fake_dispatch(
        *,
        payload: dict[str, object],
        correlation_id: str,
        settings: object,
        tenant_id: str,
    ) -> None:
        captured["payload"] = payload
        captured["correlation_id"] = correlation_id
        captured["tenant_id"] = tenant_id

    monkeypatch.setattr(webhook, "dispatch_inbound_processing", _fake_dispatch)

    request = _build_request(
        method="POST",
        body=b'{"entry": []}',
        headers={"x-correlation-id": "cid-123"},
    )

    response = await webhook.receive_webhook(request)

    assert response == {"status": "received", "correlation_id": "cid-123"}
    assert captured == {
        "payload": {"entry": []},
        "correlation_id": "cid-123",
        "tenant_id": "default",
    }


@pytest.mark.asyncio
async def test_receive_webhook_dispatch_failure_returns_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        webhook,
        "get_whatsapp_settings",
        lambda: SimpleNamespace(webhook_secret="secret", webhook_processing_mode="inline"),
    )
    monkeypatch.setattr(
        webhook,
        "parse_webhook_request",
        lambda raw_body, headers, secret: (
            {"entry": []},
            SignatureResult(valid=True, skipped=False),
        ),
    )

    async def _raise_dispatch(
        *,
        payload: dict[str, object],
        correlation_id: str,
        settings: object,
        tenant_id: str,
    ) -> None:
        raise RuntimeError("dispatch failed")

    monkeypatch.setattr(webhook, "dispatch_inbound_processing", _raise_dispatch)

    request = _build_request(
        method="POST",
        body=b'{"entry": []}',
        headers={"x-correlation-id": "cid-500"},
    )

    response = await webhook.receive_webhook(request)

    assert response.status_code == 500
    assert b"internal_error" in response.body


@pytest.mark.asyncio
async def test_receive_webhook_invalid_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        webhook,
        "get_whatsapp_settings",
        lambda: SimpleNamespace(webhook_secret="secret", webhook_processing_mode="inline"),
    )

    def _raise_invalid_signature(
        *, raw_body: bytes, headers: dict[str, str], secret: str | None
    ) -> tuple[dict[str, object], SignatureResult]:
        raise InvalidSignatureError("signature_mismatch")

    monkeypatch.setattr(webhook, "parse_webhook_request", _raise_invalid_signature)

    request = _build_request(method="POST", body=b"{}")
    response = await webhook.receive_webhook(request)

    assert response.status_code == 401
    assert response.body == b"Unauthorized"


@pytest.mark.asyncio
async def test_receive_webhook_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        webhook,
        "get_whatsapp_settings",
        lambda: SimpleNamespace(webhook_secret="secret", webhook_processing_mode="inline"),
    )

    def _raise_invalid_json(
        *, raw_body: bytes, headers: dict[str, str], secret: str | None
    ) -> tuple[dict[str, object], SignatureResult]:
        raise InvalidJsonError("invalid_json")

    monkeypatch.setattr(webhook, "parse_webhook_request", _raise_invalid_json)

    request = _build_request(method="POST", body=b"{invalid}")
    response = await webhook.receive_webhook(request)

    assert response.status_code == 400
    assert response.body == b"Bad Request"
