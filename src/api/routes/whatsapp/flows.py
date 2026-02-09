"""Endpoint de data-exchange para WhatsApp Flows."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.infra.crypto import FlowCryptoError, validate_flow_signature
from app.infra.crypto.flow_encryption import decrypt_flow_request, encrypt_flow_response
from app.services.appointment_availability import get_available_dates, get_available_times
from config.settings import get_whatsapp_settings

logger = logging.getLogger(__name__)

router = APIRouter()

_VERTICAL_LABELS: dict[str, str] = {
    "saas": "SaaS Pyloto",
    "sob_medida": "Desenvolvimento Sob Medida",
    "gestao_perfis_trafego": "Gestao de Perfis e Trafego",
    "automacao_atendimento": "Automacao de Atendimento",
    "intermediacao_entregas": "Intermediacao de Entregas",
}


@router.post("/flow/endpoint")
async def handle_flow_endpoint(request: Request) -> PlainTextResponse:
    """Recebe payload criptografado da Meta e retorna plaintext base64."""
    settings = get_whatsapp_settings()
    raw_body = await request.body()
    signature = request.headers.get("x-hub-signature-256", "")
    app_secret = settings.app_secret or settings.webhook_secret
    if not app_secret:
        logger.error(
            "flow_endpoint_misconfigured",
            extra={"component": "flow_endpoint", "missing": "app_secret"},
        )
        return PlainTextResponse("Flow endpoint misconfigured", status_code=503)
    if not validate_flow_signature(raw_body, signature, app_secret.encode("utf-8")):
        logger.warning(
            "flow_signature_invalid",
            extra={"component": "flow_endpoint", "action": "validate_signature"},
        )
        return PlainTextResponse("Signature verification failed", status_code=401)
    if not settings.flow_private_key:
        logger.error(
            "flow_endpoint_misconfigured",
            extra={"component": "flow_endpoint", "missing": "flow_private_key"},
        )
        return PlainTextResponse("Flow endpoint misconfigured", status_code=503)

    encrypted_body = _parse_encrypted_body(raw_body)
    if encrypted_body is None:
        return PlainTextResponse("Malformed request", status_code=400)

    try:
        decrypted = decrypt_flow_request(
            encrypted_flow_data_b64=encrypted_body["encrypted_flow_data"],
            encrypted_aes_key_b64=encrypted_body["encrypted_aes_key"],
            initial_vector_b64=encrypted_body["initial_vector"],
            private_key_pem=settings.flow_private_key,
            private_key_passphrase=settings.flow_private_key_passphrase or None,
        )
    except FlowCryptoError as exc:
        logger.error(
            "flow_decryption_failed",
            extra={"component": "flow_endpoint", "error_type": type(exc).__name__},
        )
        return PlainTextResponse("Decryption failed", status_code=421)

    response_payload = _route_flow_action(decrypted.payload)
    if response_payload is None:
        return PlainTextResponse("Unknown action", status_code=400)

    encrypted_response = encrypt_flow_response(
        response=response_payload,
        aes_key=decrypted.aes_key,
        iv=decrypted.iv,
    )
    return PlainTextResponse(content=encrypted_response, status_code=200)


def _parse_encrypted_body(raw_body: bytes) -> dict[str, str] | None:
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    encrypted_flow_data = payload.get("encrypted_flow_data")
    encrypted_aes_key = payload.get("encrypted_aes_key")
    initial_vector = payload.get("initial_vector")
    if not all(
        isinstance(item, str) and item
        for item in (encrypted_flow_data, encrypted_aes_key, initial_vector)
    ):
        return None
    return {
        "encrypted_flow_data": encrypted_flow_data,
        "encrypted_aes_key": encrypted_aes_key,
        "initial_vector": initial_vector,
    }


def _route_flow_action(payload: dict[str, object]) -> dict[str, object] | None:
    action = payload.get("action")
    if action == "ping":
        return {"data": {"status": "active"}}
    if action not in ("INIT", "data_exchange", "BACK"):
        logger.warning(
            "flow_unknown_action",
            extra={"component": "flow_endpoint", "action": action},
        )
        return None
    return _process_flow_logic(payload)


def _process_flow_logic(payload: dict[str, object]) -> dict[str, object]:
    action = str(payload.get("action") or "")
    screen = str(payload.get("screen") or "")
    data = payload.get("data")
    flow_data = data if isinstance(data, dict) else {}
    flow_token = str(payload.get("flow_token") or "")
    trigger = str(flow_data.get("trigger") or "")

    if action == "INIT":
        return {
            "screen": "APPOINTMENT",
            "data": {
                "vertical": [
                    {"id": key, "title": label}
                    for key, label in _VERTICAL_LABELS.items()
                ],
                "date": [],
                "is_date_enabled": False,
                "time": [],
                "is_time_enabled": False,
                "meeting_mode": "presencial",
            },
        }

    if trigger == "vertical_selected":
        dates = get_available_dates()
        return {
            "data": {
                "date": dates,
                "is_date_enabled": bool(dates),
                "time": [],
                "is_time_enabled": False,
            }
        }

    if trigger == "date_selected":
        times = get_available_times()
        return {
            "data": {
                "time": times,
                "is_time_enabled": bool(times),
            }
        }

    if screen == "APPOINTMENT":
        meeting_mode = str(flow_data.get("meeting_mode") or "presencial")
        return {
            "screen": "DETAILS",
            "data": {
                "vertical": flow_data.get("vertical", ""),
                "date": flow_data.get("date", ""),
                "time": flow_data.get("time", ""),
                "meeting_mode": meeting_mode,
            },
        }

    if screen == "DETAILS":
        vertical = str(flow_data.get("vertical") or "")
        date = str(flow_data.get("date") or "")
        time = str(flow_data.get("time") or "")
        meeting_mode = str(flow_data.get("meeting_mode") or "presencial")
        summary = (
            f"{_VERTICAL_LABELS.get(vertical, vertical)}\n"
            f"{date} as {time}\n"
            f"Modalidade sugerida: presencial"
        )
        details = _format_user_details(flow_data)
        return {
            "screen": "SUMMARY",
            "data": {
                "summary_text": summary,
                "details_text": details,
                **flow_data,
                "meeting_mode": meeting_mode,
            },
        }

    if screen == "SUMMARY":
        params = {"flow_token": flow_token, **flow_data}
        return {
            "screen": "SUCCESS",
            "data": {"extension_message_response": {"params": params}},
        }

    return {"screen": "APPOINTMENT", "data": {}}


def _format_user_details(data: dict[str, object]) -> str:
    lines = [
        f"Nome: {data.get('name') or 'N/A'!s}",
        f"Email: {data.get('email') or 'N/A'!s}",
        f"Telefone: {data.get('phone') or 'N/A'!s}",
        f"Empresa: {data.get('company') or 'N/A'!s}",
        f"Modalidade: {data.get('meeting_mode') or 'presencial'!s}",
    ]
    need = str(data.get("need_description") or "").strip()
    if need:
        lines.append(f"Necessidade: {need}")
    return "\n".join(lines)
