"""Prompt do OttoAgent (agente principal)."""

from __future__ import annotations

from ai.prompts.system_role import SYSTEM_ROLE

OTTO_SYSTEM_PROMPT = (
    SYSTEM_ROLE
    + """

INSTRUCOES GERAIS (OBRIGATORIO):
- Responda sempre em PT-BR (portugues brasileiro).
- Nunca prometa prazos, valores fechados ou resultados garantidos.
- Nunca exponha dados pessoais do usuario.
- Se houver risco ou duvida, marque requires_human=true e proponha escala.
- Nao gere instrucoes inseguras.

SAIDA OBRIGATORIA (JSON apenas):
{
  "next_state": "<ESTADO>",
  "response_text": "<texto curto e direto>",
  "message_type": "text|interactive_button|interactive_list",
  "confidence": 0.0,
  "requires_human": false,
  "reasoning_debug": "opcional"
}
"""
)

OTTO_USER_TEMPLATE = """## Contexto institucional
{institutional_context}

## Contexto do tenant (vertical)
{tenant_context}

## Resumo do ContactCard
{contact_card_summary}

## Historico curto
{conversation_history}

## Estado atual e transicoes validas
Estado atual: {session_state}
Transicoes validas: {valid_transitions}

## Mensagem atual do usuario
{user_message}

Escolha o proximo estado apenas entre as transicoes validas.
Responda apenas JSON.
"""


def format_otto_prompt(
    *,
    user_message: str,
    session_state: str,
    valid_transitions: list[str],
    institutional_context: str,
    tenant_context: str,
    contact_card_summary: str,
    conversation_history: str,
) -> str:
    """Formata prompt do OttoAgent.

    Args:
        user_message: Mensagem atual do usuario
        session_state: Estado atual
        valid_transitions: Lista de transicoes validas
        institutional_context: Contexto institucional resumido
        tenant_context: Contexto de vertente (quando houver)
        contact_card_summary: Resumo do ContactCard
        conversation_history: Historico curto (sanitizado)
    """
    return OTTO_USER_TEMPLATE.format(
        user_message=(user_message or "")[:800],
        session_state=session_state or "",
        valid_transitions=", ".join(valid_transitions) if valid_transitions else "Nenhuma",
        institutional_context=(institutional_context or "(vazio)")[:2000],
        tenant_context=(tenant_context or "(vazio)")[:1200],
        contact_card_summary=(contact_card_summary or "(vazio)")[:1200],
        conversation_history=(conversation_history or "(sem historico)")[:1200],
    )
