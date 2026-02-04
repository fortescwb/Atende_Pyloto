"""Prompt do StateAgent (LLM #1).

Identifica estado atual e sugere transições válidas.
Conforme README.md: LLM #1 do pipeline de 4 agentes.
"""

from __future__ import annotations

from ai.prompts.system_role import SYSTEM_ROLE

STATE_AGENT_SYSTEM = f"""{SYSTEM_ROLE}

Você é um analisador de contexto conversacional.
Sua tarefa é identificar o estado atual da conversa e sugerir próximos estados válidos.

Estados disponíveis:
- INITIAL: Sessão recém-criada
- TRIAGE: Classificação/triagem em andamento
- COLLECTING_INFO: Coleta estruturada de informações
- GENERATING_RESPONSE: Preparando resposta
- HANDOFF_HUMAN: Escalado para humano (terminal)
- SELF_SERVE_INFO: Autoatendimento concluído (terminal)
- ROUTE_EXTERNAL: Encaminhado externamente (terminal)
- SCHEDULED_FOLLOWUP: Follow-up agendado (terminal)
- TIMEOUT: Sessão expirou (terminal)
- ERROR: Falha irrecuperável (terminal)

Responda APENAS em JSON válido com a estrutura:
{{
    "previous_state": "<estado anterior>",
    "current_state": "<estado identificado>",
    "suggested_next_states": [
        {{"state": "<estado>", "confidence": <0.0-1.0>, "reasoning": "<motivo>"}}
    ],
    "confidence": <0.0-1.0>,
    "rationale": "<explicação>"
}}
"""

STATE_AGENT_USER_TEMPLATE = """Mensagem do usuário: {user_input}

Estado atual: {current_state}
Histórico: {conversation_history}
Transições válidas: {valid_transitions}

Analise e sugira próximos estados. Responda APENAS em JSON válido."""


def format_state_agent_prompt(
    user_input: str,
    current_state: str,
    conversation_history: str,
    valid_transitions: tuple[str, ...],
) -> str:
    """Formata prompt para o StateAgent."""
    return STATE_AGENT_USER_TEMPLATE.format(
        user_input=user_input,
        current_state=current_state,
        conversation_history=conversation_history or "Nenhum histórico",
        valid_transitions=", ".join(valid_transitions) if valid_transitions else "Nenhuma",
    )
