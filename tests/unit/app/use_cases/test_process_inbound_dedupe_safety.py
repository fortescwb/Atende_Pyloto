"""Testes de segurança do dedupe no processamento inbound."""

from __future__ import annotations

import pytest

from ai.models.otto import OttoDecision
from app.protocols.models import NormalizedMessage
from app.sessions.models import Session, SessionContext
from app.use_cases.whatsapp.process_inbound_canonical import ProcessInboundCanonicalUseCase
from fsm.states import SessionState


class _Normalizer:
    def normalize(self, payload: dict[str, object]) -> list[NormalizedMessage]:
        return [
            NormalizedMessage(
                message_id="mid-1",
                from_number="+554499999999",
                message_type="text",
                text="oi",
            )
        ]


class _SessionManager:
    def __init__(self) -> None:
        self.session = Session(
            session_id="session-1",
            sender_id="hash-1",
            current_state=SessionState.INITIAL,
            context=SessionContext(tenant_id="tenant", vertente="geral"),
            history=[],
            turn_count=0,
        )

    async def resolve_or_create(
        self,
        *,
        sender_id: str,
        tenant_id: str,
        whatsapp_name: str | None = None,
    ) -> Session:
        return self.session

    async def save(self, session: Session) -> None:
        return None

    async def close(self, session: Session, reason: str) -> None:
        return None


class _DedupeTracker:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def is_duplicate(self, message_id: str, ttl: int = 3600) -> bool:
        self.calls.append("is_duplicate")
        return False

    async def mark_processing(self, message_id: str, ttl: int = 30) -> None:
        self.calls.append("mark_processing")

    async def mark_processed(self, message_id: str, ttl: int = 3600) -> None:
        self.calls.append("mark_processed")

    async def unmark_processing(self, message_id: str) -> None:
        self.calls.append("unmark_processing")


class _Sender:
    async def send(self, request, payload):
        return type("Resp", (), {"success": True})()


class _OttoSuccess:
    async def decide(self, request):
        return OttoDecision(
            next_state="TRIAGE",
            response_text="resposta",
            message_type="text",
            confidence=0.9,
            requires_human=False,
        )


class _OttoFailure:
    async def decide(self, request):
        raise RuntimeError("otto_down")


@pytest.mark.asyncio
async def test_dedupe_marks_processed_only_after_successful_pipeline() -> None:
    dedupe = _DedupeTracker()
    usecase = ProcessInboundCanonicalUseCase(
        normalizer=_Normalizer(),
        session_manager=_SessionManager(),
        dedupe=dedupe,
        otto_agent=_OttoSuccess(),
        outbound_sender=_Sender(),
    )

    await usecase.execute(payload={"entry": []}, correlation_id="corr-1", tenant_id="tenant")

    assert dedupe.calls == ["is_duplicate", "mark_processing", "mark_processed"]


@pytest.mark.asyncio
async def test_dedupe_unmarks_processing_when_pipeline_fails() -> None:
    dedupe = _DedupeTracker()
    usecase = ProcessInboundCanonicalUseCase(
        normalizer=_Normalizer(),
        session_manager=_SessionManager(),
        dedupe=dedupe,
        otto_agent=_OttoFailure(),
        outbound_sender=_Sender(),
    )

    with pytest.raises(RuntimeError, match="otto_down"):
        await usecase.execute(payload={"entry": []}, correlation_id="corr-2", tenant_id="tenant")

    assert dedupe.calls == ["is_duplicate", "mark_processing", "unmark_processing"]
