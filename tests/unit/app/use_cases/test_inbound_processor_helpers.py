"""Cobertura adicional para helpers de _inbound_processor."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.use_cases.whatsapp._inbound_processor as inbound_processor
import app.use_cases.whatsapp._inbound_processor_context as inbound_processor_context
import app.use_cases.whatsapp._inbound_processor_mixin as inbound_processor_mixin
from ai.models.contact_card_extraction import ContactCardExtractionResult, ContactCardPatch
from ai.models.otto import OttoDecision
from app.protocols.models import NormalizedMessage
from app.services.otto_repetition_guard import GuardResult
from app.sessions.models import Session, SessionContext
from app.use_cases.whatsapp._inbound_processor import InboundMessageProcessor
from fsm.states import SessionState


class _SessionManagerStub:
    async def resolve_or_create(
        self,
        *,
        sender_id: str,
        tenant_id: str,
        whatsapp_name: str | None = None,
    ) -> Session:
        del sender_id, tenant_id, whatsapp_name
        return _build_session()

    async def save(self, session: Session) -> None:
        del session
        return None

    async def close(self, session: Session, reason: str) -> None:
        del session, reason
        return None


class _DedupeSpy:
    def __init__(self, *, duplicate: bool = False) -> None:
        self.duplicate = duplicate
        self.calls: list[str] = []

    async def is_duplicate(self, message_id: str, ttl: int = 3600) -> bool:
        del message_id, ttl
        self.calls.append("is_duplicate")
        return self.duplicate

    async def mark_processing(self, message_id: str, ttl: int = 30) -> None:
        del message_id, ttl
        self.calls.append("mark_processing")

    async def mark_processed(self, message_id: str, ttl: int = 3600) -> None:
        del message_id, ttl
        self.calls.append("mark_processed")

    async def unmark_processing(self, message_id: str) -> None:
        del message_id
        self.calls.append("unmark_processing")


class _OttoStub:
    async def decide(self, request: object) -> OttoDecision:
        del request
        return OttoDecision(
            next_state="TRIAGE",
            response_text="ok",
            message_type="text",
            confidence=0.9,
            requires_human=False,
        )


class _SenderStub:
    async def send(self, request: object, payload: object) -> object:
        del request, payload
        return type("Resp", (), {"success": True})()


def _build_session() -> Session:
    return Session(
        session_id="sess-1",
        sender_id="sender-hash",
        current_state=SessionState.INITIAL,
        context=SessionContext(tenant_id="tenant", vertente="geral"),
        history=[],
        turn_count=0,
    )


def _build_decision(text: str = "resposta") -> OttoDecision:
    return OttoDecision(
        next_state="TRIAGE",
        response_text=text,
        message_type="text",
        confidence=0.85,
        requires_human=False,
    )


def _build_processor(dedupe: _DedupeSpy) -> InboundMessageProcessor:
    return InboundMessageProcessor(
        session_manager=_SessionManagerStub(),
        dedupe=dedupe,
        otto_agent=_OttoStub(),
        outbound_sender=_SenderStub(),
    )


@pytest.mark.asyncio
async def test_process_skips_invalid_message_without_dedupe_calls() -> None:
    dedupe = _DedupeSpy()
    processor = _build_processor(dedupe)
    msg = NormalizedMessage(
        message_id="msg-skip",
        from_number=None,
        message_type="text",
        text=None,
    )

    result = await processor.process(msg=msg, correlation_id="corr", tenant_id="tenant")

    assert result is None
    assert dedupe.calls == []


@pytest.mark.asyncio
async def test_process_skips_duplicate_before_mark_processing() -> None:
    dedupe = _DedupeSpy(duplicate=True)
    processor = _build_processor(dedupe)
    msg = NormalizedMessage(
        message_id="msg-dup",
        from_number="+554499999999",
        message_type="text",
        text="oi",
    )

    result = await processor.process(msg=msg, correlation_id="corr", tenant_id="tenant")

    assert result is None
    assert dedupe.calls == ["is_duplicate"]


@pytest.mark.asyncio
async def test_process_builds_result_when_audio_fallback_sent() -> None:
    dedupe = _DedupeSpy()
    processor = _build_processor(dedupe)
    session = _build_session()
    processor._resolve_session = AsyncMock(return_value=session)
    processor._resolve_user_text = AsyncMock(return_value=(None, True))

    msg = NormalizedMessage(
        message_id="msg-audio",
        from_number="+554499999999",
        message_type="audio",
        text=None,
    )
    result = await processor.process(msg=msg, correlation_id="corr", tenant_id="tenant")

    assert result is not None
    assert result["session_id"] == "sess-1"
    assert result["final_state"] == "INITIAL"
    assert result["sent"] is True
    assert dedupe.calls == ["is_duplicate", "mark_processing", "mark_processed"]


@pytest.mark.asyncio
async def test_apply_extraction_marks_out_of_hours_and_applies_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(inbound_processor, "is_within_business_hours", lambda _: False)

    processor = SimpleNamespace(_apply_contact_card_patch=AsyncMock())
    extraction = ContactCardExtractionResult(
        updates=ContactCardPatch(
            email="lead@empresa.com",
            meeting_preferred_datetime_text="quarta as 20h",
        ),
        confidence=0.82,
    )

    extracted_fields = await inbound_processor._apply_extraction(
        processor,
        contact_card=object(),
        extraction=extraction,
        correlation_id="corr",
        message_id="msg-1",
    )

    assert "meeting_time_out_of_hours" in extracted_fields
    kwargs = processor._apply_contact_card_patch.await_args.kwargs
    assert kwargs["patch"].meeting_preferred_datetime_text is None
    assert kwargs["confidence"] == pytest.approx(0.82)


def test_apply_guards_prioritizes_business_hours_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _build_decision("base")
    adjusted = _build_decision("horario ajustado")
    processor = SimpleNamespace(_log_contact_card_snapshot=MagicMock())

    monkeypatch.setattr(
        inbound_processor,
        "_apply_business_hours_guard_log",
        lambda **_: adjusted,
    )

    def _should_not_run(**_: object) -> OttoDecision:
        raise AssertionError("Guard de repeticao nao deveria executar.")

    monkeypatch.setattr(
        inbound_processor,
        "_apply_repetition_and_continuation_guards",
        _should_not_run,
    )

    result = inbound_processor._apply_guards(
        processor,
        decision=decision,
        contact_card=object(),
        extracted_fields=[],
        user_message="oi",
        correlation_id="corr",
        message_id="msg-1",
    )

    assert result == adjusted
    processor._log_contact_card_snapshot.assert_called_once()


def test_apply_guards_uses_repetition_path_when_business_hours_not_applied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _build_decision("base")
    adjusted = _build_decision("repeticao ajustada")
    processor = SimpleNamespace(_log_contact_card_snapshot=MagicMock())

    monkeypatch.setattr(
        inbound_processor,
        "_apply_business_hours_guard_log",
        lambda **_: None,
    )
    monkeypatch.setattr(
        inbound_processor,
        "_apply_repetition_and_continuation_guards",
        lambda **_: adjusted,
    )

    result = inbound_processor._apply_guards(
        processor,
        decision=decision,
        contact_card=object(),
        extracted_fields=[],
        user_message="oi",
        correlation_id="corr",
        message_id="msg-1",
    )

    assert result == adjusted
    processor._log_contact_card_snapshot.assert_called_once()


def test_business_hours_guard_log_returns_none_when_not_applied() -> None:
    result = inbound_processor._apply_business_hours_guard_log(
        decision=_build_decision(),
        extracted_fields=[],
        correlation_id="corr",
        message_id="msg-1",
    )

    assert result is None


def test_business_hours_guard_log_returns_adjusted_decision_when_applied() -> None:
    result = inbound_processor._apply_business_hours_guard_log(
        decision=_build_decision("pode ser 20h?"),
        extracted_fields=["meeting_time_out_of_hours"],
        correlation_id="corr",
        message_id="msg-1",
    )

    assert result is not None
    assert "horario de atendimento" in result.response_text.lower()


def test_repetition_guard_path_is_preferred(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _build_decision("texto base")
    repetition_decision = _build_decision("pergunta de continuidade")

    monkeypatch.setattr(
        inbound_processor,
        "apply_repetition_guard",
        lambda **_: GuardResult(
            decision=repetition_decision,
            applied=True,
            question_type="email",
            next_question_key="company",
            guard_type="repetition",
        ),
    )

    def _continuation_not_called(**_: object) -> GuardResult:
        raise AssertionError("Continuation guard nao deveria ser chamado.")

    monkeypatch.setattr(
        inbound_processor,
        "apply_continuation_guard",
        _continuation_not_called,
    )

    result = inbound_processor._apply_repetition_and_continuation_guards(
        decision=decision,
        contact_card=object(),
        extracted_fields=[],
        user_message="ok",
        correlation_id="corr",
        message_id="msg-1",
    )

    assert result == repetition_decision


def test_continuation_guard_path_when_repetition_not_applied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _build_decision("texto base")
    continuation_decision = _build_decision("proximo passo")

    monkeypatch.setattr(
        inbound_processor,
        "apply_repetition_guard",
        lambda **_: GuardResult(decision=decision, applied=False),
    )
    monkeypatch.setattr(
        inbound_processor,
        "apply_continuation_guard",
        lambda **_: GuardResult(
            decision=continuation_decision,
            applied=True,
            next_question_key="urgency",
            guard_type="continuation",
        ),
    )

    result = inbound_processor._apply_repetition_and_continuation_guards(
        decision=decision,
        contact_card=object(),
        extracted_fields=["email"],
        user_message="confirmo",
        correlation_id="corr",
        message_id="msg-1",
    )

    assert result == continuation_decision


def test_repetition_and_continuation_return_original_when_not_applied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _build_decision("texto base")

    monkeypatch.setattr(
        inbound_processor,
        "apply_repetition_guard",
        lambda **_: GuardResult(decision=decision, applied=False),
    )
    monkeypatch.setattr(
        inbound_processor,
        "apply_continuation_guard",
        lambda **_: GuardResult(decision=decision, applied=False),
    )

    result = inbound_processor._apply_repetition_and_continuation_guards(
        decision=decision,
        contact_card=object(),
        extracted_fields=[],
        user_message="ok",
        correlation_id="corr",
        message_id="msg-1",
    )

    assert result == decision


def test_extract_contact_card_signals_keeps_only_non_empty_strings() -> None:
    card = SimpleNamespace(
        company_size=" 11-50 ",
        budget_indication="",
        specific_need="Automacao",
        company=None,
        role=" CTO ",
    )

    signals = inbound_processor_mixin._extract_contact_card_signals(card)

    assert signals == {
        "company_size": "11-50",
        "specific_need": "Automacao",
        "role": "CTO",
    }


def test_adjust_for_meeting_question_forces_collecting_info() -> None:
    decision = OttoDecision(
        next_state="TRIAGE",
        response_text="Qual melhor dia e horario para agendar?",
        message_type="text",
        confidence=0.8,
        requires_human=False,
    )

    adjusted = inbound_processor_mixin._adjust_for_meeting_question(
        decision=decision,
        valid={"TRIAGE", "COLLECTING_INFO"},
        text=decision.response_text.lower(),
        correlation_id="corr",
        message_id="msg-1",
    )

    assert adjusted is not None
    assert adjusted.next_state == "COLLECTING_INFO"


def test_adjust_for_meeting_collected_forces_scheduled_followup() -> None:
    decision = OttoDecision(
        next_state="GENERATING_RESPONSE",
        response_text="Perfeito, vou organizar os detalhes.",
        message_type="text",
        confidence=0.9,
        requires_human=False,
    )
    contact_card = SimpleNamespace(
        meeting_preferred_datetime_text="quarta 15h",
        email="lead@empresa.com",
    )

    adjusted = inbound_processor_mixin._adjust_for_meeting_collected(
        decision=decision,
        valid={"GENERATING_RESPONSE", "SCHEDULED_FOLLOWUP"},
        text=decision.response_text.lower(),
        contact_card=contact_card,
        correlation_id="corr",
        message_id="msg-1",
    )

    assert adjusted is not None
    assert adjusted.next_state == "SCHEDULED_FOLLOWUP"


@pytest.mark.asyncio
async def test_run_agents_returns_extraction_when_parallel_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _OttoWithCount(_OttoStub):
        def __init__(self) -> None:
            self.calls = 0

        async def decide(self, request: object) -> OttoDecision:
            del request
            self.calls += 1
            return _build_decision("ok")

    dedupe = _DedupeSpy()
    processor = _build_processor(dedupe)
    otto = _OttoWithCount()
    processor._otto_agent = otto

    async def _fake_extraction() -> object:
        return {"email": "lead@empresa.com"}

    monkeypatch.setattr(
        processor,
        "_build_extraction_task",
        lambda **_: _fake_extraction(),
    )

    otto_request, decision, extraction = await processor._run_agents(
        session=_build_session(),
        sanitized_input="oi",
        history=["usuario: oi"],
        contact_card=object(),
        card_summary="",
        raw_user_text="oi",
        correlation_id="corr-run-agents-ok",
    )

    assert otto_request.user_message == "oi"
    assert decision.response_text == "ok"
    assert extraction == {"email": "lead@empresa.com"}
    assert otto.calls == 1


@pytest.mark.asyncio
async def test_run_agents_fallbacks_to_otto_when_parallel_times_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _OttoWithCount(_OttoStub):
        def __init__(self) -> None:
            self.calls = 0

        async def decide(self, request: object) -> OttoDecision:
            del request
            self.calls += 1
            return _build_decision("fallback")

    dedupe = _DedupeSpy()
    processor = _build_processor(dedupe)
    otto = _OttoWithCount()
    processor._otto_agent = otto

    async def _slow_extraction() -> object:
        await asyncio.sleep(0.05)
        return {"email": "x@x.com"}

    monkeypatch.setattr(
        processor,
        "_build_extraction_task",
        lambda **_: _slow_extraction(),
    )
    monkeypatch.setattr(inbound_processor_context, "_AGENTS_PARALLEL_TIMEOUT_SECONDS", 0.001)
    monkeypatch.setattr(inbound_processor_mixin, "_AGENTS_PARALLEL_TIMEOUT_SECONDS", 0.001)

    otto_request, decision, extraction = await processor._run_agents(
        session=_build_session(),
        sanitized_input="oi",
        history=["usuario: oi"],
        contact_card=object(),
        card_summary="",
        raw_user_text="oi",
        correlation_id="corr-run-agents-timeout",
    )

    assert otto_request.user_message == "oi"
    assert decision.response_text == "fallback"
    assert extraction is None
    assert otto.calls == 2
