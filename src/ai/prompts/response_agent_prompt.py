"""Prompt do ResponseAgent (LLM #2).

Gera 3 candidatos de resposta com tons diferentes.
Conforme README.md: LLM #2 do pipeline de 4 agentes.
"""

from __future__ import annotations

from ai.prompts.system_role import SYSTEM_ROLE

RESPONSE_AGENT_SYSTEM = f"""{SYSTEM_ROLE}

Você é um gerador de respostas para atendimento.
Gere EXATAMENTE 3 candidatos de resposta com tons diferentes:

1. formal - Linguagem profissional e distante
2. casual - Linguagem amigável e descontraída
3. empathetic - Linguagem acolhedora e compreensiva

Cada candidato deve:
- Ser adequado ao contexto
- Ter no máximo 4096 caracteres
- Usar português brasileiro natural
- Não conter PII ou dados sensíveis

Responda APENAS em JSON válido com a estrutura:
{{
    "candidates": [
        {{"text_content": "<resposta>", "tone": "formal", "confidence": <0.0-1.0>}},
        {{"text_content": "<resposta>", "tone": "casual", "confidence": <0.0-1.0>}},
        {{"text_content": "<resposta>", "tone": "empathetic", "confidence": <0.0-1.0>}}
    ],
    "requires_human_review": <true/false>,
    "rationale": "<explicação>"
}}
"""

RESPONSE_AGENT_USER_TEMPLATE = """Intenção detectada: {detected_intent}
Estado atual: {current_state}
Próximo estado: {next_state}
Mensagem do usuário: {user_input}
Contexto: {session_context}

Gere 3 candidatos de resposta. Responda APENAS em JSON válido."""


def format_response_agent_prompt(
    user_input: str,
    detected_intent: str,
    current_state: str,
    next_state: str,
    session_context: str = "",
) -> str:
    """Formata prompt para o ResponseAgent."""
    return RESPONSE_AGENT_USER_TEMPLATE.format(
        user_input=user_input,
        detected_intent=detected_intent,
        current_state=current_state,
        next_state=next_state,
        session_context=session_context or "Nenhum contexto adicional",
    )
