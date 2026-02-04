"""Prompt do StateAgent (Agente 1) — gpt-5-nano.

Seletor de estado: recebe últimas 3 mensagens e estados possíveis.
Retorna apenas: próximo estado + confiança.

CONTEXTO MÍNIMO para velocidade:
- Últimas 3 mensagens do usuário
- Estado anterior, atual e próximos possíveis
"""

from __future__ import annotations

# Prompt minimalista para nano — apenas seleção de estado
STATE_AGENT_SYSTEM = """Selecione o próximo estado da conversa.

ESTADOS:
- INITIAL: Sessão recém-criada
- TRIAGE: Classificação em andamento
- COLLECTING_INFO: Coletando informações do cliente
- GENERATING_RESPONSE: Preparando resposta
- HANDOFF_HUMAN: Escalar para humano
- SELF_SERVE_INFO: Autoatendimento concluído
- ROUTE_EXTERNAL: Encaminhar para sistema externo
- SCHEDULED_FOLLOWUP: Follow-up agendado
- TIMEOUT: Encerrar por inatividade
- ERROR: Erro inesperado

REGRAS:
- Se usuário está frustrado → HANDOFF_HUMAN
- Se precisa coletar dados → COLLECTING_INFO
- Se pode responder direto → GENERATING_RESPONSE
- Se é primeira mensagem → TRIAGE
- Sempre respeite os próximos válidos

Responda APENAS em JSON:
{
  "previous_state": "<ESTADO>",
  "current_state": "<ESTADO>",
  "suggested_next_states": [
    {"state": "<ESTADO>", "confidence": <0.0-1.0>, "reasoning": "<curto>"},
    {"state": "<ESTADO>", "confidence": <0.0-1.0>, "reasoning": "<curto>"}
  ],
  "confidence": <0.0-1.0>,
  "rationale": "<explicação curta>"
}
"""

STATE_AGENT_USER_TEMPLATE = """Estado anterior: {previous_state}
Estado atual: {current_state}
Próximos válidos: {valid_transitions}

Últimas mensagens:
{last_messages}

Mensagem atual: {user_input}

Escolha próximo estado. JSON apenas."""


def format_state_agent_prompt(
    user_input: str,
    current_state: str,
    conversation_history: str,
    valid_transitions: tuple[str, ...],
    previous_state: str = "INITIAL",
) -> str:
    """Formata prompt para o StateAgent.

    Args:
        user_input: Mensagem atual do usuário
        current_state: Estado atual da FSM
        conversation_history: Últimas 3 mensagens formatadas
        valid_transitions: Tupla de estados válidos para transição
        previous_state: Estado anterior
    """
    return STATE_AGENT_USER_TEMPLATE.format(
        user_input=user_input[:200],  # Trunca para nano
        current_state=current_state,
        previous_state=previous_state,
        valid_transitions=", ".join(valid_transitions) if valid_transitions else "Nenhuma",
        last_messages=conversation_history[:500] if conversation_history else "Primeira mensagem",
    )
