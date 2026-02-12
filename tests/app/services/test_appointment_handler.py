"""Testes para persistência de agendamentos de Flow."""

from __future__ import annotations

from typing import Any

import pytest
from tests.fakes.fake_calendar_service import FakeCalendarService

from app.services import appointment_handler


def test_parse_flow_completion_payload_supports_extension_params() -> None:
    payload = {
        "extension_message_response": {
            "params": {
                "flow_token": "554499999999",
                "vertical": "automacao_atendimento",
            }
        }
    }

    parsed = appointment_handler.parse_flow_completion_payload(payload)

    assert parsed == {
        "flow_token": "554499999999",
        "vertical": "automacao_atendimento",
    }


@pytest.mark.asyncio
async def test_save_appointment_from_flow_persists_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class _Document:
        def set(self, data, merge=False):
            captured["data"] = data
            captured["merge"] = merge

    class _Collection:
        def document(self, doc_id: str):
            captured["doc_id"] = doc_id
            return _Document()

    class _Firestore:
        def collection(self, name: str):
            captured["collection"] = name
            return _Collection()

    monkeypatch.setattr(appointment_handler, "create_firestore_client", lambda: _Firestore())

    result = await appointment_handler.save_appointment_from_flow(
        flow_response_json={
            "extension_message_response": {
                "params": {
                    "flow_token": "554499999999",
                    "vertical": "sob_medida",
                    "date": "2026-02-20",
                    "time": "14:00",
                    "name": "Maria",
                    "email": "M@EXAMPLE.COM",
                }
            }
        },
        from_number="+554499999999",
        correlation_id="corr-1",
    )

    assert result is not None
    assert captured["collection"] == "appointments"
    assert str(captured["doc_id"]).startswith("554499999999_2026-02-20_14:00_")
    assert captured["merge"] is True
    assert captured["data"]["status"] == "confirmed"
    assert captured["data"]["email"] == "m@example.com"


def _patch_firestore_client(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    captured: dict[str, Any] = {"writes": []}

    class _Document:
        def set(self, data: dict[str, Any], merge: bool = False) -> None:
            # Guardamos writes em memoria para validar efeitos sem IO real.
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


@pytest.mark.asyncio
async def test_save_appointment_creates_calendar_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _patch_firestore_client(monkeypatch)
    calendar_service = FakeCalendarService()

    result = await appointment_handler.save_appointment_from_flow(
        flow_response_json={
            "extension_message_response": {
                "params": {
                    "flow_token": "554499999999",
                    "vertical": "sob_medida",
                    "date": "2026-02-20",
                    "time": "14:00",
                    "name": "Maria",
                    "email": "maria@example.com",
                }
            }
        },
        from_number="+554499999999",
        correlation_id="corr-2",
        calendar_service=calendar_service,
    )

    assert result is not None
    assert "calendar_event_id" in result
    assert "calendar_html_link" in result
    assert captured["collection"] == "appointments"
    created_event = await calendar_service.get_event(result["calendar_event_id"])
    assert created_event is not None


@pytest.mark.asyncio
async def test_save_appointment_without_calendar_keeps_compatibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_firestore_client(monkeypatch)

    result = await appointment_handler.save_appointment_from_flow(
        flow_response_json={
            "extension_message_response": {
                "params": {
                    "flow_token": "554499999999",
                    "vertical": "automacao",
                    "date": "2026-02-20",
                    "time": "15:00",
                    "name": "Joao",
                    "email": "joao@example.com",
                }
            }
        },
        from_number="+554499999999",
        correlation_id="corr-3",
    )

    assert result is not None
    assert "calendar_event_id" not in result


@pytest.mark.asyncio
async def test_save_appointment_calendar_failure_does_not_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_firestore_client(monkeypatch)

    class _FailingCalendar:
        async def create_event(self, appointment: Any) -> Any:
            _ = appointment
            raise Exception("calendar offline")

    result = await appointment_handler.save_appointment_from_flow(
        flow_response_json={
            "extension_message_response": {
                "params": {
                    "flow_token": "554499999999",
                    "vertical": "saas",
                    "date": "2026-02-20",
                    "time": "16:00",
                    "name": "Ana",
                    "email": "ana@example.com",
                }
            }
        },
        from_number="+554499999999",
        correlation_id="corr-4",
        calendar_service=_FailingCalendar(),
    )

    assert result is not None
    assert "calendar_event_id" not in result
