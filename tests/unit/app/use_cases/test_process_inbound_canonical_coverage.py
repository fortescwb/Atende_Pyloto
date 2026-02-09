"""Cobertura adicional para ProcessInboundCanonicalUseCase."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.protocols.models import NormalizedMessage
from app.use_cases.whatsapp.process_inbound_canonical import ProcessInboundCanonicalUseCase


class _SessionStore:
    def __init__(self) -> None:
        self.load_async = AsyncMock(return_value=None)
        self.save_async = AsyncMock()
        self.delete_async = AsyncMock(return_value=True)


class _NoopSessionManager:
    async def resolve_or_create(
        self,
        *,
        sender_id: str,
        tenant_id: str,
        whatsapp_name: str | None = None,
    ) -> object:
        raise AssertionError("Nao deveria resolver sessao neste teste.")

    async def save(self, session: object) -> None:
        return None

    async def close(self, session: object, reason: str) -> None:
        return None


class _NoopDedupe:
    async def is_duplicate(self, message_id: str, ttl: int = 3600) -> bool:
        return False

    async def mark_processing(self, message_id: str, ttl: int = 30) -> None:
        return None

    async def mark_processed(self, message_id: str, ttl: int = 3600) -> None:
        return None

    async def unmark_processing(self, message_id: str) -> None:
        return None


class _NoopOtto:
    async def decide(self, request: object) -> object:
        raise AssertionError("Nao deveria chamar Otto neste teste.")


class _NoopSender:
    async def send(self, request: object, payload: object) -> object:
        return type("Resp", (), {"success": True})()


class _SingleMessageNormalizer:
    def normalize(self, payload: dict[str, Any]) -> list[NormalizedMessage]:
        return [
            NormalizedMessage(
                message_id="msg-1",
                from_number="+554499999999",
                message_type="text",
                text="oi",
            )
        ]


class _ThreeMessagesNormalizer:
    def normalize(self, payload: dict[str, Any]) -> list[NormalizedMessage]:
        return [
            NormalizedMessage(
                message_id="msg-1",
                from_number="+554499999999",
                message_type="text",
                text="primeira",
            ),
            NormalizedMessage(
                message_id="msg-2",
                from_number="+554499999999",
                message_type="text",
                text="segunda",
            ),
            NormalizedMessage(
                message_id="msg-3",
                from_number="+554499999999",
                message_type="text",
                text="terceira",
            ),
        ]


def test_constructor_uses_session_store_when_manager_not_provided() -> None:
    store = _SessionStore()

    use_case = ProcessInboundCanonicalUseCase(
        normalizer=_SingleMessageNormalizer(),
        session_store=store,
        dedupe=_NoopDedupe(),
        otto_agent=_NoopOtto(),
        outbound_sender=_NoopSender(),
    )

    assert use_case._session_manager.__class__.__name__ == "SessionManager"
    assert use_case._session_manager._store is store


def test_constructor_requires_session_dependency() -> None:
    with pytest.raises(ValueError, match="Either session_manager or session_store"):
        ProcessInboundCanonicalUseCase(
            normalizer=_SingleMessageNormalizer(),
            dedupe=_NoopDedupe(),
            otto_agent=_NoopOtto(),
            outbound_sender=_NoopSender(),
        )


@pytest.mark.asyncio
async def test_execute_counts_skipped_processed_and_sent() -> None:
    use_case = ProcessInboundCanonicalUseCase(
        normalizer=_ThreeMessagesNormalizer(),
        session_manager=_NoopSessionManager(),
        dedupe=_NoopDedupe(),
        otto_agent=_NoopOtto(),
        outbound_sender=_NoopSender(),
    )

    class _ProcessorSequence:
        def __init__(self) -> None:
            self._results = [
                None,
                {
                    "session_id": "sess-1",
                    "final_state": "TRIAGE",
                    "closed": False,
                    "sent": False,
                },
                {
                    "session_id": "sess-2",
                    "final_state": "SCHEDULED_FOLLOWUP",
                    "closed": True,
                    "sent": True,
                },
            ]

        async def process(
            self,
            msg: NormalizedMessage,
            correlation_id: str,
            tenant_id: str,
        ) -> dict[str, Any] | None:
            del msg, correlation_id, tenant_id
            return self._results.pop(0)

    use_case._processor = _ProcessorSequence()
    result = await use_case.execute(
        payload={"entry": []},
        correlation_id="corr-1",
        tenant_id="tenant",
    )

    assert result.processed == 2
    assert result.skipped == 1
    assert result.sent == 1
    assert result.session_id == "sess-2"
    assert result.final_state == "SCHEDULED_FOLLOWUP"
    assert result.closed is True
