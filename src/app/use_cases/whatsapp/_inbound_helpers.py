"""Helpers internos para o use case de inbound canônico.

Extrai lógica auxiliar para reduzir o tamanho do process_inbound_canonical.py.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Protocol

from ai.rules.intent_detection import detect_intent
from fsm.states import SessionState
from fsm.transitions.rules import get_valid_targets

if TYPE_CHECKING:
    from app.protocols import OutboundMessageRequest
    from app.protocols.models import NormalizedMessage


class OutboundDecisionProtocol(Protocol):
    """Contrato mínimo para construção de payload outbound."""

    response_text: str | None
    message_type: str | None
    final_text: str | None
    final_message_type: str | None

logger = logging.getLogger(__name__)


def map_state_suggestion_to_target(
    state_result: Any,
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
    decision: OutboundDecisionProtocol,
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
    msg_type = _resolve_message_type(decision)
    text = _resolve_text(decision)

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
            emoji = text or "👍"
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
        payload["text"] = {"body": text}
    elif msg_type in ("interactive_button", "interactive_list"):
        payload["type"] = "interactive"
        payload["interactive"] = {
            "type": "button" if "button" in msg_type else "list",
            "body": {"text": text},
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
    decision: OutboundDecisionProtocol,
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
        message_type=_resolve_message_type(decision),
        text=_resolve_text(decision),
        idempotency_key=f"{correlation_id}:{msg.message_id}:response",
    )


def serialize_contact_card(contact_card: Any) -> str:
    """Serializa ContactCard para JSON seguro no prompt."""
    if contact_card is None:
        return "{}"
    try:
        payload = contact_card.model_dump(exclude_none=True, mode="json")
        return json.dumps(payload, ensure_ascii=False)
    except Exception:
        return "{}"


def _resolve_message_type(decision: OutboundDecisionProtocol) -> str:
    msg_type = getattr(decision, "message_type", None) or getattr(
        decision, "final_message_type", None
    )
    return msg_type or "text"


def _resolve_text(decision: OutboundDecisionProtocol) -> str:
    return (
        getattr(decision, "response_text", None)
        or getattr(decision, "final_text", None)
        or ""
    )

def history_as_strings(session: Any) -> list[str]:
    history = getattr(session, "history_as_strings", None)
    if history is not None:
        return list(history)
    raw_history = getattr(session, "history", []) or []
    return [str(entry) for entry in raw_history]

def user_history_as_strings(session: Any, *, max_messages: int = 5) -> list[str]:
    """Retorna somente as últimas N mensagens do usuário (sem mensagens do bot)."""
    raw_history = getattr(session, "history", []) or []
    user_messages: list[str] = []
    for entry in raw_history:
        if isinstance(entry, str):
            user_messages.append(entry)
            continue
        if isinstance(entry, dict):
            if entry.get("role") == "user" and entry.get("content"):
                user_messages.append(f"Usuario: {entry['content']}")
            continue
        role = getattr(entry, "role", None)
        content = getattr(entry, "content", None)
        role_value = getattr(role, "value", role)
        if role_value == "user" and content:
            user_messages.append(f"Usuario: {content}")

    if max_messages <= 0:
        return user_messages
    return user_messages[-max_messages:]

def last_assistant_message(session: Any) -> str:
    """Retorna a ultima mensagem do assistente, se existir."""
    raw_history = getattr(session, "history", []) or []
    for entry in reversed(raw_history):
        if isinstance(entry, str):
            lowered = entry.lower()
            if lowered.startswith("otto:") or lowered.startswith("assistente:"):
                return entry.split(":", 1)[-1].strip()
            continue
        if isinstance(entry, dict):
            if entry.get("role") == "assistant" and entry.get("content"):
                return str(entry["content"]).strip()
            continue
        role = getattr(entry, "role", None)
        content = getattr(entry, "content", None)
        role_value = getattr(role, "value", role)
        if role_value == "assistant" and content:
            return str(content).strip()
    return ""

def build_tenant_intent(session: Any, user_message: str) -> tuple[str | None, float]:
    """Detecta vertente e retorna (intent, confidence).

    Prioridade:
      1) ContactCard.primary_interest (alta confiança)
      2) Contexto da sessão (última vertente)
      3) Heurística por keywords
    """
    contact_card = getattr(session, "contact_card", None)
    primary = getattr(contact_card, "primary_interest", None) if contact_card is not None else None
    if isinstance(primary, str) and primary.strip():
        return primary.strip(), 0.9

    prior_intent = getattr(getattr(session, "context", None), "prompt_vertical", "") or ""
    if isinstance(prior_intent, str) and prior_intent.strip():
        return prior_intent.strip(), 0.7

    detected = detect_intent(user_message)
    return detected, 0.6 if detected else 0.0

def get_valid_transitions(current_state: SessionState) -> tuple[str, ...]:
    return tuple(state.name for state in get_valid_targets(current_state))

def is_terminal_session(session: Any) -> bool:
    return bool(getattr(session, "is_terminal", False))
