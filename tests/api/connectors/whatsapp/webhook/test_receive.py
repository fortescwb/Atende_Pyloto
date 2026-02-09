import hashlib
import hmac
import json

import pytest

from api.connectors.whatsapp.webhook.receive import (
    InvalidJsonError,
    InvalidSignatureError,
    parse_webhook_request,
)


def _sign(payload: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_parse_webhook_request_ok() -> None:
    secret = "secret"
    body = json.dumps({"entry": []}).encode("utf-8")
    headers = {"x-hub-signature-256": _sign(body, secret)}

    payload, result = parse_webhook_request(body, headers, secret)

    assert payload == {"entry": []}
    assert result.valid is True


def test_parse_webhook_request_invalid_signature() -> None:
    secret = "secret"
    body = json.dumps({"entry": []}).encode("utf-8")
    headers = {"x-hub-signature-256": "sha256=deadbeef"}

    with pytest.raises(InvalidSignatureError, match="signature"):
        parse_webhook_request(body, headers, secret)


def test_parse_webhook_request_invalid_json() -> None:
    secret = "secret"
    body = b"{invalid}"
    headers = {"x-hub-signature-256": _sign(body, secret)}

    with pytest.raises(InvalidJsonError, match="invalid_json"):
        parse_webhook_request(body, headers, secret)
