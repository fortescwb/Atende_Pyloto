import hashlib
import json

from api.connectors.whatsapp.event_id import compute_inbound_event_id


def test_compute_inbound_event_id_uses_message_id() -> None:
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {"id": "msg_123", "type": "text"}
                            ]
                        }
                    }
                ]
            }
        ]
    }
    raw = json.dumps(payload).encode("utf-8")

    assert compute_inbound_event_id(payload, raw) == "msg_123"


def test_compute_inbound_event_id_fallback_hash() -> None:
    payload = {"entry": []}
    raw = b""

    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    expected = f"payload:{digest}"

    assert compute_inbound_event_id(payload, raw) == expected
