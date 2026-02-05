"""Testes do OttoClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infra.ai.otto_client import OttoClient


class FakeResponse:
    def __init__(self, content: str) -> None:
        message = MagicMock()
        message.content = content
        choice = MagicMock()
        choice.message = message
        self.choices = [choice]


def _build_fake_openai(content: str) -> MagicMock:
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=FakeResponse(content))
    return client


@pytest.mark.asyncio
async def test_decide_parses_valid_json() -> None:
    fake_openai = _build_fake_openai(
        '{"next_state": "TRIAGE", "response_text": "Oi", "message_type": "text", '
        '"confidence": 0.9, "requires_human": false}'
    )
    client = OttoClient(client=fake_openai, model="gpt-4o", timeout_seconds=10)

    result = await client.decide(system_prompt="s", user_prompt="u")

    assert result is not None
    assert result.next_state == "TRIAGE"
    assert result.message_type == "text"


@pytest.mark.asyncio
async def test_decide_returns_none_on_invalid_json() -> None:
    fake_openai = _build_fake_openai("nao json")
    client = OttoClient(client=fake_openai, model="gpt-4o", timeout_seconds=10)

    result = await client.decide(system_prompt="s", user_prompt="u")

    assert result is None
