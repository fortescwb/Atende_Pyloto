"""Use case canônico para processamento inbound WhatsApp.

Integra pipeline de 4 agentes LLM conforme README.md.

NOTA: Este arquivo tem ~217 linhas (ligeiramente acima de 200).
Justificativa: Classe principal do fluxo inbound, já usa helpers externos.
Dividir mais comprometeria a legibilidade do fluxo principal.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ai.utils.sanitizer import sanitize_pii

# Dependências por protocolo (injetadas) -- evita acoplamento a implementações
from app.use_cases.whatsapp._inbound_helpers import (
    build_outbound_payload,
    build_outbound_request,
    map_state_suggestion_to_target,
)
from fsm.manager import FSMStateMachine

if TYPE_CHECKING:
    from ai.services.orchestrator import AIOrchestrator
    from app.protocols import (
        AsyncDedupeProtocol,
        AsyncSessionStoreProtocol,
        DecisionAuditStoreProtocol,
        MessageNormalizerProtocol,
        OutboundSenderProtocol,
    )
    from app.protocols.master_decider import MasterDeciderProtocol, MasterDecision
    from app.protocols.models import NormalizedMessage
    from app.protocols.session_manager import SessionManagerProtocol

logger = logging.getLogger(__name__)


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
    """Processa mensagem inbound seguindo fluxo canônico."""

    def __init__(
        self,
        *,
        normalizer: MessageNormalizerProtocol,
        session_store: AsyncSessionStoreProtocol | None = None,
        session_manager: SessionManagerProtocol | None = None,
        dedupe: AsyncDedupeProtocol,
        ai_orchestrator: AIOrchestrator,
        outbound_sender: OutboundSenderProtocol,
        audit_store: DecisionAuditStoreProtocol | None = None,
        master_decider: MasterDeciderProtocol | None = None,
    ) -> None:
        """Inicializa use case com dependências. Preferir injeção de protocolos.

        Para compatibilidade, aceita `session_store` e `master_decider` concretos e
        criará os adaptadores locais apenas se necessário.
        """
        self._normalizer = normalizer

        # session_manager: prefer protocol; fallback: constrói a partir de session_store
        if session_manager is not None:
            self._session_manager = session_manager
        elif session_store is not None:
            # Import local para evitar acoplamento em nível de módulo
            from app.sessions.manager import SessionManager

            self._session_manager = SessionManager(session_store)
        else:
            raise ValueError("Either session_manager or session_store must be provided")

        self._dedupe = dedupe
        self._ai_orchestrator = ai_orchestrator
        self._outbound_sender = outbound_sender
        self._audit_store = audit_store

        # master_decider: prefer protocol; fallback: implementação padrão
        if master_decider is not None:
            self._master_decider = master_decider
        else:
            from app.services.master_decider import MasterDecider

            self._master_decider = MasterDecider()

    async def execute(
        self,
        *,
        payload: dict[str, Any],
        correlation_id: str,
        tenant_id: str = "",
    ) -> InboundProcessingResult:
        """Executa fluxo canônico de processamento inbound."""
        messages = self._normalizer.normalize(payload)
        processed, skipped, sent = 0, 0, 0
        session_id, final_state, closed = "", "ENTRY", False

        for msg in messages:
            result = await self._process_single_message(msg, correlation_id, tenant_id)
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

    async def _process_single_message(
        self,
        msg: NormalizedMessage,
        correlation_id: str,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        """Processa uma única mensagem normalizada."""
        if not msg.from_number or not msg.text:
            return None

        if await self._dedupe.is_duplicate(msg.message_id):
            return None
        await self._dedupe.mark_processed(msg.message_id)

        session = await self._session_manager.resolve_or_create(
            sender_id=msg.from_number,
            tenant_id=tenant_id,
        )
        sanitized_input = sanitize_pii(msg.text)

        # Transições válidas a partir do estado atual
        valid_transitions = self._get_valid_transitions(session.current_state.name)

        # 3-7) AI Orchestrator (4 agentes LLM)
        ai_result = await self._ai_orchestrator.process_message(
            user_input=sanitized_input,
            current_state=session.current_state.name,
            session_history=session.history,
            valid_transitions=valid_transitions,
            session_context={
                "tenant_id": session.context.tenant_id,
                "vertente": session.context.vertente,
                "turn_count": str(session.turn_count),
            },
        )

        # 4) FSM - usa sugestão do StateAgent (LLM #1)
        fsm = FSMStateMachine(
            initial_state=session.current_state,
            session_id=session.session_id,
        )
        target_state = map_state_suggestion_to_target(
            ai_result.state_suggestion,
            session.current_state,
        )
        fsm_result = fsm.transition(
            target=target_state,
            trigger="inbound_message",
            metadata={
                "correlation_id": correlation_id,
                "understood": ai_result.understood,
            },
            confidence=ai_result.overall_confidence,
        )

        # 6) Decisor mestre
        decision = self._master_decider.decide(
            session=session,
            ai_result=ai_result,
            fsm_result=fsm_result,
            user_input=sanitized_input,
        )

        if self._audit_store:
            self._audit_store.append(decision.audit_record)

        # 8) Outbound
        sent = await self._send_response(msg, decision, correlation_id)

        # 9) Atualiza sessão
        if fsm_result.success and fsm_result.transition:
            session.transition_to(fsm_result.transition.to_state)
        session.add_to_history(sanitized_input)
        await self._session_manager.save(session)

        if decision.should_close_session:
            reason = decision.close_reason or "normal"
            await self._session_manager.close(session, reason)

        return {
            "session_id": session.session_id,
            "final_state": decision.final_state,
            "closed": decision.should_close_session,
            "sent": sent,
        }

    def _get_valid_transitions(self, current_state: str) -> tuple[str, ...]:
        """Retorna transições válidas a partir do estado atual."""
        # Mapa simplificado de transições válidas
        transitions = {
            "INITIAL": ("TRIAGE", "COLLECTING_INFO"),
            "TRIAGE": ("COLLECTING_INFO", "GENERATING_RESPONSE", "HANDOFF_HUMAN"),
            "COLLECTING_INFO": ("GENERATING_RESPONSE", "HANDOFF_HUMAN", "TRIAGE"),
            "GENERATING_RESPONSE": ("SELF_SERVE_INFO", "HANDOFF_HUMAN", "TRIAGE"),
        }
        return transitions.get(current_state, ("TRIAGE",))

    async def _send_response(
        self,
        msg: NormalizedMessage,
        decision: MasterDecision,
        correlation_id: str,
    ) -> bool:
        """Envia resposta outbound."""
        try:
            request = build_outbound_request(msg, decision, correlation_id)
            recipient = msg.from_number or ""
            if recipient and not recipient.startswith("+"):
                recipient = f"+{recipient}"
            payload = build_outbound_payload(
                decision, recipient, reply_to_message_id=msg.message_id
            )
            response = await self._outbound_sender.send(request, payload)
            return response.success
        except Exception as exc:
            logger.error(
                "outbound_send_failed",
                extra={
                    "correlation_id": correlation_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return False
