"""Testes para o handler inbound WhatsApp."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.coordinators.whatsapp.inbound.handler import process_inbound_payload
from app.use_cases.whatsapp.process_inbound_canonical import InboundProcessingResult


@dataclass
class MockUseCase:
    """Mock do ProcessInboundCanonicalUseCase para testes."""

    result: InboundProcessingResult

    async def execute(
        self,
        *,
        payload: dict[str, Any],
        correlation_id: str,
        tenant_id: str = "",
    ) -> InboundProcessingResult:
        return self.result


class TestProcessInboundPayload:
    """Testes para process_inbound_payload."""

    @pytest.mark.asyncio
    async def test_process_inbound_payload_success(self) -> None:
        """Deve processar payload e retornar resultado do use case."""
        expected_result = InboundProcessingResult(
            session_id="session-123",
            processed=1,
            skipped=0,
            sent=1,
            final_state="GENERATING_RESPONSE",
            closed=False,
        )
        mock_use_case = MockUseCase(result=expected_result)

        payload = {"entry": [{"changes": [{"value": {"messages": []}}]}]}

        result = await process_inbound_payload(
            payload=payload,
            correlation_id="corr-123",
            use_case=mock_use_case,  # type: ignore[arg-type]
            tenant_id="tenant-1",
        )

        assert result.session_id == "session-123"
        assert result.processed == 1
        assert result.skipped == 0
        assert result.sent == 1
        assert result.final_state == "GENERATING_RESPONSE"
        assert result.closed is False

    @pytest.mark.asyncio
    async def test_process_inbound_payload_with_skipped(self) -> None:
        """Deve retornar contagem de mensagens ignoradas."""
        expected_result = InboundProcessingResult(
            session_id="session-456",
            processed=2,
            skipped=3,
            sent=2,
            final_state="TRIAGE",
            closed=False,
        )
        mock_use_case = MockUseCase(result=expected_result)

        result = await process_inbound_payload(
            payload={},
            correlation_id="corr-456",
            use_case=mock_use_case,  # type: ignore[arg-type]
        )

        assert result.processed == 2
        assert result.skipped == 3

    @pytest.mark.asyncio
    async def test_process_inbound_payload_session_closed(self) -> None:
        """Deve indicar quando sessão foi encerrada."""
        expected_result = InboundProcessingResult(
            session_id="session-789",
            processed=1,
            skipped=0,
            sent=1,
            final_state="TIMEOUT",
            closed=True,
        )
        mock_use_case = MockUseCase(result=expected_result)

        result = await process_inbound_payload(
            payload={},
            correlation_id="corr-789",
            use_case=mock_use_case,  # type: ignore[arg-type]
        )

        assert result.closed is True
        assert result.final_state == "TIMEOUT"
