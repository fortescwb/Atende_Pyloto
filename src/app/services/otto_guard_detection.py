"""Deteccao deterministica de perguntas e confirmacoes do Otto.

Este modulo existe para manter `otto_repetition_guard.py` pequeno (<=200 linhas)
e com responsabilidade clara: identificar "tipo" de pergunta para suportar guards.
"""

from __future__ import annotations

import unicodedata


def detect_question_type(text: str) -> str | None:
    """Tenta inferir sobre qual campo o Otto esta perguntando."""
    normalized = _normalize(text)
    if not normalized:
        return None
    if not _looks_like_question(normalized):
        return None

    if _contains_any(normalized, _MEETING_DATETIME_KEYWORDS):
        return "meeting_preferred_datetime_text"
    if _contains_any(normalized, _EMAIL_KEYWORDS):
        return "email"
    if _contains_any(normalized, _FULL_NAME_KEYWORDS):
        return "full_name"
    if _contains_any(normalized, _COMPANY_KEYWORDS):
        return "company"

    if _contains_any(normalized, _MESSAGE_VOLUME_KEYWORDS):
        return "message_volume_per_day"
    if _contains_any(normalized, _ATTENDANTS_KEYWORDS):
        return "attendants_count"
    if _contains_any(normalized, _SPECIALISTS_KEYWORDS):
        return "specialists_count"
    if _contains_any(normalized, _CRM_KEYWORDS):
        return "has_crm"
    if _contains_any(normalized, _TOOLS_KEYWORDS):
        return "current_tools"

    if _contains_any(normalized, _USERS_COUNT_KEYWORDS):
        return "users_count"
    if _contains_any(normalized, _MODULES_KEYWORDS):
        return "modules_needed"
    if _contains_any(normalized, _FEATURES_KEYWORDS):
        return "desired_features"
    if _contains_any(normalized, _INTEGRATIONS_KEYWORDS):
        return "integrations_needed"
    if _contains_any(normalized, _MIGRATION_KEYWORDS):
        return "needs_data_migration"

    return None


def is_confirmation_message(text: str) -> bool:
    normalized = _normalize(text)
    return normalized in {
        "isso",
        "sim",
        "ok",
        "certo",
        "exato",
        "perfeito",
        "beleza",
        "blz",
        "aham",
        "uhum",
    }


def _looks_like_question(text: str) -> bool:
    if "?" in text:
        return True
    starts = ("qual ", "quais ", "quant", "voce ", "voces ", "ja ", "tem ", "usa ")
    return text.strip().startswith(starts)


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)

def _normalize(text: str) -> str:
    lowered = (text or "").strip().lower()
    if not lowered:
        return ""
    no_accents = "".join(
        ch for ch in unicodedata.normalize("NFKD", lowered) if not unicodedata.combining(ch)
    )
    return " ".join(no_accents.split())


_MEETING_DATETIME_KEYWORDS = (
    "qual melhor dia",
    "qual melhor horario",
    "qual melhor dia e horario",
    "dia e horario",
    "dia/horario",
    "marcar uma conversa",
    "agendar",
    "podemos marcar",
)

_FULL_NAME_KEYWORDS = (
    "qual seu nome",
    "seu nome completo",
    "como voce se chama",
    "como voces se chamam",
)

_EMAIL_KEYWORDS = ("email", "e-mail")

_COMPANY_KEYWORDS = (
    "empresa",
    "nome da empresa",
    "nome do escritorio",
    "escritorio",
)

_MESSAGE_VOLUME_KEYWORDS = (
    "mensagens por dia",
    "mensagens/dia",
    "volume de mensagens",
    "quantas mensagens",
    "qtd mensagens",
    "quantidade de mensagens",
    "atendimentos por dia",
    "volume diario",
)

_ATTENDANTS_KEYWORDS = (
    "quantas pessoas atendem",
    "quantas pessoas atendendo",
    "pessoas atendendo",
    "equipe de atendimento",
    "quantos atendentes",
    "time de atendimento",
)

_SPECIALISTS_KEYWORDS = (
    "quantos advogados",
    "quantos especialistas",
    "quantos profissionais",
    "quantos consultores",
)

_CRM_KEYWORDS = (
    "crm",
    "integra com crm",
    "integracao com crm",
    "ja usa crm",
    "ja tem crm",
    "usa crm",
    "tem crm",
)

_TOOLS_KEYWORDS = (
    "planilha",
    "whatsapp web",
    "ferramenta",
    "ferramentas",
    "como se organizam",
    "como organizam",
)

_USERS_COUNT_KEYWORDS = (
    "quantos usuarios",
    "qtd usuarios",
    "quantas pessoas vao usar",
    "quantas pessoas usariam",
)

_MODULES_KEYWORDS = ("modulos", "crm", "agenda", "financeiro")

_FEATURES_KEYWORDS = ("funcionalidade", "funcionalidades", "requisitos", "o que precisa")

_INTEGRATIONS_KEYWORDS = ("integracao", "integracoes", "integrar", "api", "erp", "whatsapp")

_MIGRATION_KEYWORDS = ("migracao", "migrar dados", "importar dados", "legado")
