"""Testes de extração de mensagens WhatsApp (helpers)."""

from __future__ import annotations

import json

from api.normalizers.whatsapp._extraction_helpers import extract_interactive_message


def test_extract_interactive_message_with_nfm_reply_response_json() -> None:
    msg = {
        "interactive": {
            "type": "nfm_reply",
            "nfm_reply": {
                "response_json": {
                    "flow_token": "554499999999",
                    "date": "2026-02-20",
                    "time": "14:00",
                }
            },
        }
    }

    interactive_type, button_id, list_id, flow_response_json = extract_interactive_message(msg)

    assert interactive_type == "nfm_reply"
    assert button_id is None
    assert list_id is None
    assert json.loads(flow_response_json or "{}") == {
        "flow_token": "554499999999",
        "date": "2026-02-20",
        "time": "14:00",
    }
