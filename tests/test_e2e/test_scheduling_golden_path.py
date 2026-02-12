"""Teste E2E do caminho de agendamento via completion do Flow."""

from __future__ import annotations

from typing import Any

import pytest
from tests.fakes.fake_calendar_service import FakeCalendarService

from app.services import appointment_handler


def _build_valid_flow_payload() -> dict[str, Any]:
    return {
        "extension_message_response": {
            "params": {
                "flow_token": "554499999999",
                "vertical": "sob_medida",
                "date": "2026-02-20",
                "time": "14:00",
                "name": "Maria",
                "email": "maria@example.com",
                "meeting_mode": "online",
            }
        }
    }


def _patch_firestore_client(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    captured: dict[str, Any] = {"writes": []}

    class _Document:
        def set(self, data: dict[str, Any], merge: bool = False) -> None:
            # Capturamos os writes para validar o efeito sem chamar Firestore real.
            captured["writes"].append({"data": data, "merge": merge})

    class _Collection:
        def document(self, doc_id: str) -> _Document:
            captured["doc_id"] = doc_id
            return _Document()

    class _Firestore:
        def collection(self, name: str) -> _Collection:
            captured["collection"] = name
            return _Collection()

    monkeypatch.setattr(appointment_handler, "create_firestore_client", lambda: _Firestore())
    return captured


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_flow_completion_creates_calendar_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_firestore_client(monkeypatch)
    calendar_service = FakeCalendarService()
    payload = _build_valid_flow_payload()

    parsed = appointment_handler.parse_flow_completion_payload(payload)
    result = await appointment_handler.save_appointment_from_flow(
        flow_response_json=payload,
        from_number="+554499999999",
        correlation_id="corr-e2e-1",
        calendar_service=calendar_service,
    )

    assert parsed is not None
    assert result is not None
    assert "calendar_event_id" in result
    stored_event = await calendar_service.get_event(result["calendar_event_id"])
    assert stored_event is not None


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_flow_completion_without_calendar_still_saves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_firestore_client(monkeypatch)

    result = await appointment_handler.save_appointment_from_flow(
        flow_response_json=_build_valid_flow_payload(),
        from_number="+554499999999",
        correlation_id="corr-e2e-2",
    )

    assert result is not None
    assert "calendar_event_id" not in result


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_flow_completion_invalid_payload_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_firestore_client(monkeypatch)

    result = await appointment_handler.save_appointment_from_flow(
        flow_response_json={},
        from_number="+554499999999",
        correlation_id="corr-e2e-3",
    )

    assert result is None
