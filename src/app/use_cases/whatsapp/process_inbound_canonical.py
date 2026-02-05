"""Use case canônico para processamento inbound WhatsApp.

Fluxo novo (Otto + utilitários):
- normaliza + dedupe
- se audio: transcreve
- carrega ContactCard (Firestore)
- paralelo: OttoAgent + ContactCardExtractor
- aplica patch e persiste
- envia resposta e atualiza sessão
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.use_cases.whatsapp._inbound_processor import InboundMessageProcessor

if TYPE_CHECKING:
    from ai.services.contact_card_extractor import ContactCardExtractorService
    from ai.services.decision_validator import DecisionValidatorService
    from ai.services.otto_agent import OttoAgentService
    from app.protocols import (
        AsyncDedupeProtocol,
        AsyncSessionStoreProtocol,
        MessageNormalizerProtocol,
        OutboundSenderProtocol,
    )
    from app.protocols.contact_card_store import ContactCardStoreProtocol
    from app.protocols.session_manager import SessionManagerProtocol
    from app.protocols.transcription_service import TranscriptionServiceProtocol


@dataclass(frozen=True, slots=True)
class InboundProcessingResult:
    """Resultado do processamento inbound."""

    session_id: str
    processed: int
    skipped: int
    sent: int
    final_state: str
    closed: bool


class ProcessInboundCanonicalUseCase:
    """Processa mensagem inbound seguindo fluxo canônico (Otto + utilitários)."""

    def __init__(
        self,
        *,
        normalizer: MessageNormalizerProtocol,
        session_store: AsyncSessionStoreProtocol | None = None,
        session_manager: SessionManagerProtocol | None = None,
        dedupe: AsyncDedupeProtocol,
        otto_agent: OttoAgentService,
        decision_validator: DecisionValidatorService | None = None,
        outbound_sender: OutboundSenderProtocol,
        contact_card_store: ContactCardStoreProtocol | None = None,
        transcription_service: TranscriptionServiceProtocol | None = None,
        contact_card_extractor: ContactCardExtractorService | None = None,
    ) -> None:
        self._normalizer = normalizer

        if session_manager is not None:
            self._session_manager = session_manager
        elif session_store is not None:
            from app.sessions.manager import SessionManager

            self._session_manager = SessionManager(session_store)
        else:
            raise ValueError("Either session_manager or session_store must be provided")

        self._processor = InboundMessageProcessor(
            session_manager=self._session_manager,
            dedupe=dedupe,
            otto_agent=otto_agent,
            decision_validator=decision_validator,
            outbound_sender=outbound_sender,
            contact_card_store=contact_card_store,
            transcription_service=transcription_service,
            contact_card_extractor=contact_card_extractor,
        )

    async def execute(
        self,
        *,
        payload: dict[str, Any],
        correlation_id: str,
        tenant_id: str = "",
    ) -> InboundProcessingResult:
        messages = self._normalizer.normalize(payload)
        processed, skipped, sent = 0, 0, 0
        session_id, final_state, closed = "", "ENTRY", False

        for msg in messages:
            result = await self._processor.process(msg, correlation_id, tenant_id)
            if result is None:
                skipped += 1
                continue
            session_id, final_state = result["session_id"], result["final_state"]
            closed = result["closed"]
            processed += 1
            if result["sent"]:
                sent += 1

        return InboundProcessingResult(
            session_id=session_id,
            processed=processed,
            skipped=skipped,
            sent=sent,
            final_state=final_state,
            closed=closed,
        )
