"""Persistência de agendamentos concluídos via WhatsApp Flow."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.bootstrap.clients import create_firestore_client

logger = logging.getLogger(__name__)

_APPOINTMENTS_COLLECTION = "appointments"


def parse_flow_completion_payload(
    flow_response_json: str | dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Extrai payload de completion a partir do response_json do nfm_reply."""
    if not flow_response_json:
        return None
    payload: dict[str, Any]
    if isinstance(flow_response_json, str):
        try:
            loaded = json.loads(flow_response_json)
        except json.JSONDecodeError:
            return None
        if not isinstance(loaded, dict):
            return None
        payload = loaded
    elif isinstance(flow_response_json, dict):
        payload = flow_response_json
    else:
        return None

    extension = payload.get("extension_message_response")
    if isinstance(extension, dict):
        params = extension.get("params")
        if isinstance(params, dict):
            return params

    params = payload.get("params")
    if isinstance(params, dict):
        return params

    return payload


async def save_appointment_from_flow(
    *,
    flow_response_json: str | dict[str, Any] | None,
    from_number: str | None,
    correlation_id: str | None,
) -> dict[str, Any] | None:
    """Salva agendamento de completion no Firestore."""
    parsed = parse_flow_completion_payload(flow_response_json)
    if not parsed:
        return None

    wa_id = str(parsed.get("flow_token") or from_number or "").strip()
    if not wa_id:
        return None

    record = {
        "wa_id": wa_id,
        "vertical": _str_or_empty(parsed.get("vertical")),
        "date": _str_or_empty(parsed.get("date")),
        "time": _str_or_empty(parsed.get("time")),
        "meeting_mode": _normalize_meeting_mode(parsed.get("meeting_mode")),
        "name": _str_or_empty(parsed.get("name")),
        "email": _str_or_empty(parsed.get("email")).lower(),
        "phone": _str_or_empty(parsed.get("phone")),
        "company": _str_or_empty(parsed.get("company")),
        "need_description": _str_or_empty(parsed.get("need_description")),
        "status": "confirmed",
        "source": "whatsapp_flow",
        "created_at": datetime.now(tz=UTC).isoformat(),
        "raw_params": parsed,
    }

    firestore_client = create_firestore_client()
    doc_id = _appointment_doc_id(wa_id=wa_id, date=record["date"], time=record["time"])
    await asyncio.to_thread(
        firestore_client.collection(_APPOINTMENTS_COLLECTION).document(doc_id).set,
        record,
        merge=True,
    )
    logger.info(
        "appointment_saved",
        extra={
            "component": "appointment_handler",
            "result": "saved",
            "correlation_id": correlation_id,
            "wa_id": wa_id,
            "date": record["date"],
            "time": record["time"],
        },
    )
    return record


def _appointment_doc_id(*, wa_id: str, date: str, time: str) -> str:
    base = f"{wa_id}|{date}|{time}"
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:12]
    return f"{wa_id}_{date}_{time}_{digest}".replace(" ", "_")


def _normalize_meeting_mode(value: Any) -> str:
    mode = _str_or_empty(value).strip().lower()
    if mode in {"online", "presencial"}:
        return mode
    return "presencial"


def _str_or_empty(value: Any) -> str:
    return str(value).strip() if value is not None else ""
