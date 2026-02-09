"""Serviço determinístico para respostas fixas de WhatsApp (Quebra-gelos e comandos)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from app.constants.whatsapp_fixed_replies import FIXED_REPLIES, FixedReplyConfig

_OTTO_INTRO = "Voce esta sendo atendido pelo Otto, assistente virtual da Pyloto."


@dataclass(frozen=True, slots=True)
class FixedReply:
    """Resposta fixa resolvida para envio ao usuário."""

    key: str
    response_text: str
    message_type: str
    prompt_vertical: str | None
    kind: Literal["quick_reply", "command"]


def match_fixed_reply(user_message: str | None) -> FixedReply | None:
    """Retorna resposta fixa se o texto for quebra-gelo ou comando conhecido."""
    if not user_message:
        return None

    command = _extract_command(user_message)
    if command:
        config = _COMMAND_INDEX.get(command)
        if config:
            return _to_reply(config)

    normalized = _normalize_text(user_message)
    if not normalized:
        return None

    config = _QUICK_REPLY_INDEX.get(normalized)
    if config:
        return _to_reply(config)

    return None


def _to_reply(config: FixedReplyConfig) -> FixedReply:
    return FixedReply(
        key=config.key,
        response_text=_ensure_otto_intro(config.response_text),
        message_type="text",
        prompt_vertical=config.prompt_vertical,
        kind=config.kind,
    )


def _ensure_otto_intro(response_text: str) -> str:
    body = (response_text or "").strip()
    if not body:
        return _OTTO_INTRO
    normalized = _normalize_text(body)
    if normalized.startswith(_normalize_text(_OTTO_INTRO)):
        return body
    return f"{_OTTO_INTRO} {body}"


def _extract_command(text: str) -> str | None:
    raw = (text or "").strip()
    if not raw.startswith("/"):
        return None
    first = raw.split()[0]
    normalized = _normalize_text(first)
    return normalized or None


def _normalize_text(text: str) -> str:
    cleaned = (text or "").strip().lower()
    if not cleaned:
        return ""
    no_accents = "".join(
        ch for ch in unicodedata.normalize("NFKD", cleaned) if not unicodedata.combining(ch)
    )
    sanitized = re.sub(r"[^a-z0-9/_]+", " ", no_accents)
    return " ".join(sanitized.split())


def _build_indexes(
    items: tuple[FixedReplyConfig, ...],
) -> tuple[dict[str, FixedReplyConfig], dict[str, FixedReplyConfig]]:
    command_index: dict[str, FixedReplyConfig] = {}
    quick_index: dict[str, FixedReplyConfig] = {}

    for item in items:
        normalized = _normalize_text(item.trigger)
        if not normalized:
            continue
        if item.kind == "command":
            command_index[normalized] = item
        else:
            quick_index[normalized] = item

    return command_index, quick_index


_COMMAND_INDEX, _QUICK_REPLY_INDEX = _build_indexes(FIXED_REPLIES)
