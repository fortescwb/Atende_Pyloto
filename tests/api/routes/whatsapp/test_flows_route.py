"""Testes do endpoint de WhatsApp Flow data-exchange."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from starlette.requests import Request

from api.routes.whatsapp import flows


def _build_request(
    *,
    method: str,
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
        "path": "/flow/endpoint",
        "raw_path": b"/flow/endpoint",
        "query_string": b"",
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


def _sign(payload: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _encrypted_payload(flow_payload: dict[str, object]) -> tuple[dict[str, str], bytes, bytes]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    aes_key = os.urandom(16)
    iv = os.urandom(12)
    encrypted_flow_data = AESGCM(aes_key).encrypt(
        iv,
        json.dumps(flow_payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
        None,
    )
    encrypted_aes_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=SHA256()),
            algorithm=SHA256(),
            label=None,
        ),
    )
    body = {
        "encrypted_flow_data": base64.b64encode(encrypted_flow_data).decode("utf-8"),
        "encrypted_aes_key": base64.b64encode(encrypted_aes_key).decode("utf-8"),
        "initial_vector": base64.b64encode(iv).decode("utf-8"),
    }
    body["private_pem"] = private_pem
    return body, aes_key, iv


@pytest.mark.asyncio
async def test_flow_endpoint_ping_success(monkeypatch: pytest.MonkeyPatch) -> None:
    encrypted, aes_key, iv = _encrypted_payload(
        {"action": "ping", "flow_token": "t", "screen": "APPOINTMENT", "data": {}, "version": "1"}
    )
    private_pem = encrypted.pop("private_pem")
    raw_body = json.dumps(encrypted).encode("utf-8")
    secret = "meta_app_secret"
    monkeypatch.setattr(
        flows,
        "get_whatsapp_settings",
        lambda: SimpleNamespace(
            app_secret=secret,
            webhook_secret="",
            flow_private_key=private_pem,
            flow_private_key_passphrase="",
        ),
    )
    request = _build_request(
        method="POST",
        body=raw_body,
        headers={"x-hub-signature-256": _sign(raw_body, secret)},
    )

    response = await flows.handle_flow_endpoint(request)

    assert response.status_code == 200
    encrypted_response = base64.b64decode(response.body.decode("utf-8"))
    flipped_iv = bytes(byte ^ 0xFF for byte in iv)
    decrypted = AESGCM(aes_key).decrypt(flipped_iv, encrypted_response, None)
    assert json.loads(decrypted.decode("utf-8")) == {"data": {"status": "active"}}


@pytest.mark.asyncio
async def test_flow_endpoint_rejects_invalid_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    encrypted, _, _ = _encrypted_payload(
        {"action": "ping", "flow_token": "t", "screen": "APPOINTMENT", "data": {}, "version": "1"}
    )
    private_pem = encrypted.pop("private_pem")
    raw_body = json.dumps(encrypted).encode("utf-8")
    monkeypatch.setattr(
        flows,
        "get_whatsapp_settings",
        lambda: SimpleNamespace(
            app_secret="secret",
            webhook_secret="",
            flow_private_key=private_pem,
            flow_private_key_passphrase="",
        ),
    )
    request = _build_request(
        method="POST",
        body=raw_body,
        headers={"x-hub-signature-256": "sha256=deadbeef"},
    )

    response = await flows.handle_flow_endpoint(request)

    assert response.status_code == 401
    assert response.body == b"Signature verification failed"


@pytest.mark.asyncio
async def test_flow_endpoint_rejects_malformed_body(monkeypatch: pytest.MonkeyPatch) -> None:
    raw_body = b'{"invalid": true}'
    secret = "secret"
    monkeypatch.setattr(
        flows,
        "get_whatsapp_settings",
        lambda: SimpleNamespace(
            app_secret=secret,
            webhook_secret="",
            flow_private_key="pem",
            flow_private_key_passphrase="",
        ),
    )
    request = _build_request(
        method="POST",
        body=raw_body,
        headers={"x-hub-signature-256": _sign(raw_body, secret)},
    )

    response = await flows.handle_flow_endpoint(request)

    assert response.status_code == 400
    assert response.body == b"Malformed request"


@pytest.mark.asyncio
async def test_flow_endpoint_returns_421_on_decrypt_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_body = json.dumps(
        {
            "encrypted_flow_data": base64.b64encode(b"bad-data").decode("utf-8"),
            "encrypted_aes_key": base64.b64encode(b"bad-key").decode("utf-8"),
            "initial_vector": base64.b64encode(b"bad-iv").decode("utf-8"),
        }
    ).encode("utf-8")
    secret = "secret"
    monkeypatch.setattr(
        flows,
        "get_whatsapp_settings",
        lambda: SimpleNamespace(
            app_secret=secret,
            webhook_secret="",
            flow_private_key="-----BEGIN PRIVATE KEY-----\ninvalid\n-----END PRIVATE KEY-----",
            flow_private_key_passphrase="",
        ),
    )
    request = _build_request(
        method="POST",
        body=raw_body,
        headers={"x-hub-signature-256": _sign(raw_body, secret)},
    )

    response = await flows.handle_flow_endpoint(request)

    assert response.status_code == 421
    assert response.body == b"Decryption failed"
