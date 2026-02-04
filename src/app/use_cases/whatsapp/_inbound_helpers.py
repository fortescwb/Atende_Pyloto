"""Helpers internos para o use case de inbound canônico.

Extrai lógica auxiliar para reduzir o tamanho do processo_inbound_canonical.py.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fsm.states import SessionState

if TYPE_CHECKING:
    from ai.models.state_agent import StateAgentResult
    from app.protocols import OutboundMessageRequest
    from app.protocols.models import NormalizedMessage
    from app.services.master_decider import MasterDecision

logger = logging.getLogger(__name__)


def map_state_suggestion_to_target(
    state_result: StateAgentResult,
    current_state: SessionState,
) -> SessionState:
    """Mapeia sugestão do StateAgent para estado FSM.

    Args:
        state_result: Resultado do StateAgent (LLM #1)
        current_state: Estado atual

    Returns:
        Estado alvo para transição
    """
    if not state_result.suggested_next_states:
        return current_state

    # Pega sugestão de maior confiança
    best = max(state_result.suggested_next_states, key=lambda s: s.confidence)

    # Valida se é um estado válido
    try:
        return SessionState[best.state]
    except KeyError:
        return current_state


def build_outbound_payload(
    decision: MasterDecision,
    recipient: str,
    reply_to_message_id: str | None = None,
) -> dict[str, str | dict[str, str]]:
    """Monta payload mínimo para outbound.

    Args:
        decision: Decisão do decisor mestre
        recipient: Destinatário (número E.164)
        reply_to_message_id: ID da mensagem original (para reactions)

    Returns:
        Payload formatado para API WhatsApp
    """
    msg_type = decision.final_message_type

    # Reaction requer formato especial
    if msg_type == "reaction":
        if not reply_to_message_id:
            logger.warning(
                "reaction_without_message_id",
                extra={"recipient": recipient[:6] + "***"},
            )
            # Fallback: enviar texto em vez de reaction
            msg_type = "text"
        else:
            emoji = decision.final_text or "👍"
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient,
                "type": "reaction",
                "reaction": {
                    "message_id": reply_to_message_id,
                    "emoji": emoji,
                },
            }

    payload: dict[str, str | dict[str, str]] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": msg_type,
    }

    if msg_type == "text":
        payload["text"] = {"body": decision.final_text}
    elif msg_type in ("interactive_button", "interactive_list"):
        payload["type"] = "interactive"
        payload["interactive"] = {
            "type": "button" if "button" in msg_type else "list",
            "body": {"text": decision.final_text},
        }
    else:
        # Fallback para tipos não suportados: enviar como texto
        logger.warning(
            "unsupported_message_type_fallback",
            extra={"original_type": msg_type, "fallback": "text"},
        )
        payload["type"] = "text"
        payload["text"] = {"body": decision.final_text}

    return payload


def build_outbound_request(
    msg: NormalizedMessage,
    decision: MasterDecision,
    correlation_id: str,
) -> OutboundMessageRequest:
    """Cria OutboundMessageRequest a partir da decisão.

    Args:
        msg: Mensagem original
        decision: Decisão do decisor mestre
        correlation_id: ID de correlação

    Returns:
        Request formatado
    """
    from app.protocols import OutboundMessageRequest

    recipient = msg.from_number
    if recipient and not recipient.startswith("+"):
        recipient = f"+{recipient}"

    return OutboundMessageRequest(
        to=recipient or "",
        message_type=decision.final_message_type,
        text=decision.final_text,
        idempotency_key=f"{correlation_id}:{msg.message_id}:response",
    )
