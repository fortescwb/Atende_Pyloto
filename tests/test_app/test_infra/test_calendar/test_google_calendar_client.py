"""Testes unitarios para o client de Google Calendar."""

from __future__ import annotations

import importlib
import sys
import types
from datetime import UTC
from types import SimpleNamespace
from typing import Any

import pytest


def _ensure_google_test_stubs() -> None:
    if "google.oauth2.service_account" not in sys.modules:
        google_module = sys.modules.setdefault("google", types.ModuleType("google"))
        oauth2_module = sys.modules.setdefault("google.oauth2", types.ModuleType("google.oauth2"))
        service_account_module = types.ModuleType("google.oauth2.service_account")

        class _Credentials:
            @staticmethod
            def from_service_account_info(info: dict[str, Any], scopes: list[str]) -> object:
                _ = (info, scopes)
                return object()

        service_account_module.Credentials = _Credentials
        oauth2_module.service_account = service_account_module
        google_module.oauth2 = oauth2_module
        sys.modules["google.oauth2.service_account"] = service_account_module

    if "googleapiclient.errors" not in sys.modules:
        google_api_module = sys.modules.setdefault(
            "googleapiclient",
            types.ModuleType("googleapiclient"),
        )
        errors_module = types.ModuleType("googleapiclient.errors")
        discovery_module = types.ModuleType("googleapiclient.discovery")

        class HttpError(Exception):
            def __init__(self, *, resp: Any, content: bytes, uri: str | None = None) -> None:
                super().__init__("http_error")
                self.resp = resp
                self.content = content
                self.uri = uri

        def _build_stub(*args: Any, **kwargs: Any) -> object:
            _ = (args, kwargs)
            return object()

        errors_module.HttpError = HttpError
        discovery_module.build = _build_stub
        google_api_module.errors = errors_module
        google_api_module.discovery = discovery_module
        sys.modules["googleapiclient.errors"] = errors_module
        sys.modules["googleapiclient.discovery"] = discovery_module


_ensure_google_test_stubs()

HttpError = importlib.import_module("googleapiclient.errors").HttpError

AppointmentData = importlib.import_module("app.domain.appointment").AppointmentData
GoogleCalendarClient = importlib.import_module(
    "app.infra.calendar.google_calendar_client"
).GoogleCalendarClient


def _build_client(monkeypatch: pytest.MonkeyPatch) -> GoogleCalendarClient:
    def _fake_init(
        self: GoogleCalendarClient,
        *,
        calendar_id: str,
        credentials_json: str,
        timezone: str,
    ) -> None:
        # Evita autenticacao real para manter o teste deterministico e sem rede.
        _ = (credentials_json, timezone)
        self._calendar_id = calendar_id
        self._timezone = "UTC"
        self._zone = UTC
        self._service = object()

    monkeypatch.setattr(GoogleCalendarClient, "__init__", _fake_init)
    return GoogleCalendarClient(
        calendar_id="calendar-1",
        credentials_json="{}",
        timezone="UTC",
    )


def _build_http_error(status: int) -> HttpError:
    # Construimos apenas o atributo minimo lido pelo parser de status.
    response = SimpleNamespace(status=status, reason="error")
    return HttpError(resp=response, content=b"error")


def _build_appointment() -> AppointmentData:
    return AppointmentData(
        date="2026-02-20",
        time="14:00",
        duration_min=30,
        attendee_name="Maria",
        attendee_email="maria@example.com",
        attendee_phone="+554499999999",
        description="Reuniao inicial",
        meeting_mode="online",
        vertical="automacao",
    )


@pytest.mark.asyncio
async def test_check_availability_returns_slots_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _build_client(monkeypatch)
    response = {
        "calendars": {
            "calendar-1": {
                "busy": [
                    {
                        "start": "2026-02-20T10:00:00+00:00",
                        "end": "2026-02-20T10:30:00+00:00",
                    }
                ]
            }
        }
    }
    monkeypatch.setattr(client, "_query_freebusy_sync", lambda body: response)

    slots = await client.check_availability("2026-02-20", start_hour=9, end_hour=12)

    assert len(slots) == 2
    assert slots[0].start.isoformat() == "2026-02-20T09:00:00+00:00"
    assert slots[0].end.isoformat() == "2026-02-20T10:00:00+00:00"
    assert slots[1].start.isoformat() == "2026-02-20T10:30:00+00:00"
    assert slots[1].end.isoformat() == "2026-02-20T12:00:00+00:00"


@pytest.mark.asyncio
async def test_check_availability_returns_empty_on_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _build_client(monkeypatch)
    error = _build_http_error(503)

    def _raise_http_error(body: dict[str, Any]) -> dict[str, Any]:
        _ = body
        raise error

    monkeypatch.setattr(client, "_query_freebusy_sync", _raise_http_error)

    slots = await client.check_availability("2026-02-20")

    assert slots == []


@pytest.mark.asyncio
async def test_create_event_returns_calendar_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _build_client(monkeypatch)
    captured: dict[str, Any] = {}

    def _insert_event(body: dict[str, Any], include_conference: bool) -> dict[str, Any]:
        captured["body"] = body
        captured["include_conference"] = include_conference
        return {
            "id": "evt-123",
            "htmlLink": "https://calendar.google.com/event?eid=evt-123",
            "start": {"dateTime": "2026-02-20T14:00:00+00:00"},
            "end": {"dateTime": "2026-02-20T14:30:00+00:00"},
            "status": "confirmed",
        }

    monkeypatch.setattr(client, "_insert_event_sync", _insert_event)

    result = await client.create_event(_build_appointment())

    assert result.event_id == "evt-123"
    assert result.html_link.endswith("evt-123")
    assert captured["include_conference"] is True
    assert "conferenceData" in captured["body"]


@pytest.mark.asyncio
async def test_create_event_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client(monkeypatch)
    error = _build_http_error(403)

    def _raise_http_error(body: dict[str, Any], include_conference: bool) -> dict[str, Any]:
        _ = (body, include_conference)
        raise error

    monkeypatch.setattr(client, "_insert_event_sync", _raise_http_error)

    with pytest.raises(HttpError):
        await client.create_event(_build_appointment())
