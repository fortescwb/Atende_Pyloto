"""Prompt do ContactCardExtractor (Agente utilitario).

Extrai somente informacoes novas para preencher ContactCard.
"""

from __future__ import annotations

CONTACT_CARD_EXTRACTOR_SYSTEM = """Voce eh um extrator de dados do ContactCard.

OBJETIVO:
- Retornar APENAS um patch com informacoes NOVAS que ainda NAO existem no ContactCard.
- Nunca inventar. Nunca inferir. Somente o que estiver explicitamente na mensagem atual.

REGRAS CRITICAS:
- NUNCA sobrescreva campos ja preenchidos no ContactCard.
- Se um campo ja existir (mesmo parcialmente), nao retorne esse campo.
- Se nao houver informacao nova, retorne updates vazio.

CAMPOS POSSIVEIS (somente se novos):
- full_name, email, company, role, location
- primary_interest: saas | sob_medida | gestao_perfis
  | trafego_pago | automacao_atendimento | intermediacao
- secondary_interests: lista de interesses adicionais
- urgency: low | medium | high | urgent
- budget_indication, specific_need, company_size (mei | micro | pequena | media | grande)
- requested_human, showed_objection

OUTPUT (JSON valido):
{
  "updates": { ... },
  "confidence": 0.0-1.0,
  "evidence": ["trechos curtos sem PII"]  # opcional
}

Se nenhuma informacao nova:
{"updates": {}, "confidence": 1.0, "evidence": []}

Responda SOMENTE JSON.
"""

CONTACT_CARD_EXTRACTOR_USER_TEMPLATE = """## ContactCard atual (JSON)
{contact_card}

## Contexto recente (opcional)
{conversation_context}

## Mensagem atual do usuario
{user_message}

Extraia apenas informacoes novas. JSON apenas."""


def format_contact_card_extractor_prompt(
    *,
    user_message: str,
    contact_card: str,
    conversation_context: str = "",
) -> str:
    """Formata prompt do ContactCardExtractor.

    Args:
        user_message: Mensagem atual do usuario
        contact_card: ContactCard serializado (JSON)
        conversation_context: Contexto recente (opcional)
    """
    return CONTACT_CARD_EXTRACTOR_USER_TEMPLATE.format(
        user_message=(user_message or "")[:600],
        contact_card=(contact_card or "{}")[:2000],
        conversation_context=conversation_context[:600] if conversation_context else "(vazio)",
    )
