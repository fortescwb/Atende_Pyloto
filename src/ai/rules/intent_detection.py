"""Detecção simples de intenção (vertical) a partir de texto.

Heurística determinística (sem LLM) para escolher um contexto vertical
quando o ContactCard ainda não tem `primary_interest`.
"""

from __future__ import annotations

import unicodedata


def detect_intent(message: str) -> str | None:
    """Detecta intenção do lead e retorna o ID curto da vertente.

    Retornos possíveis (file-basename em `src/ai/contexts/vertentes/`):
      - "entregas"
      - "automacao"
      - "trafego"

    Args:
        message: Texto do usuário.
    """
    msg = _normalize(message)
    if not msg:
        return None

    if any(word in msg for word in ("entrega", "motoboy", "delivery", "frete")):
        return "entregas"

    if any(word in msg for word in ("whatsapp", "bot", "automacao", "atendimento", "chatbot")):
        return "automacao"

    if any(
        word in msg
        for word in (
            "trafego",
            "anuncio",
            "facebook ads",
            "meta ads",
            "google ads",
            "instagram ads",
        )
    ):
        return "trafego"

    return None


def _normalize(text: str) -> str:
    lowered = (text or "").strip().lower()
    if not lowered:
        return ""
    no_accents = "".join(
        ch for ch in unicodedata.normalize("NFKD", lowered) if not unicodedata.combining(ch)
    )
    return " ".join(no_accents.split())
