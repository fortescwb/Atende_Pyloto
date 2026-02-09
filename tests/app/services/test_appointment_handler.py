"""Testes para persistência de agendamentos de Flow."""

from __future__ import annotations

import pytest

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
