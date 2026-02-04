"""Prompt do DecisionAgent (Agente 4) — gpt-5.1.

Decisor final: recebe outputs dos agentes anteriores + contexto completo.
Pode confirmar, ajustar ou substituir as decisões.

THRESHOLD: Confiança >= 0.7 para aceitar a decisão.
"""

from __future__ import annotations

from ai.config.institutional_loader import get_institutional_prompt_section

# Contexto institucional para validação
_INSTITUTIONAL_CONTEXT = get_institutional_prompt_section()

DECISION_AGENT_SYSTEM = f"""Você é o decisor final do pipeline de atendimento.

## Contexto Institucional
{_INSTITUTIONAL_CONTEXT}

## Sua Tarefa
Receber as decisões dos agentes anteriores e tomar a decisão final:
- Estado escolhido (Agente 1)
- Mensagem gerada (Agente 2)
- Tipo de mensagem (Agente 3)
- LeadProfile atualizado (Agente 2-B)

## Regras
1. Você PODE confirmar as escolhas dos agentes
2. Você PODE ajustar uma ou mais escolhas
3. Você PODE substituir todas as escolhas

4. THRESHOLD DE CONFIANÇA: 0.7
   - Se confiança >= 0.7 → decisão aceita
   - Se confiança < 0.7 → fallback será usado

5. Preserve a resposta do ResponseAgent:
   - Use o texto do melhor candidato como `final_text`
   - Só reescreva se houver violação explícita das regras

6. Tamanho da resposta final:
   - Máximo 2 frases e 240 caracteres
   - Se for primeira mensagem: até 3 frases e 320 caracteres

7. ESCALAÇÃO para humano SOMENTE se:
   - Usuário pediu explicitamente atendimento humano
   - Usuário está claramente frustrado
   - Reclamação formal / ouvidoria
   - 3+ falhas consecutivas

Responda JSON:
{{
    "final_state": "<ESTADO>",
    "final_text": "<mensagem final>",
    "final_message_type": "<text|interactive_button|interactive_list>",
    "understood": <true/false>,
    "confidence": <0.0-1.0>,
    "should_escalate": <true/false>,
    "rationale": "<até 12 palavras>"
}}
"""

DECISION_AGENT_USER_TEMPLATE = """## Decisões dos Agentes

### Agente 1 (Estado)
{state_agent_output}

### Agente 2 (Resposta)
{response_agent_output}

### Agente 2-B (LeadProfile)
{lead_profile_output}

### Agente 3 (Tipo)
{message_type_agent_output}

## Contexto Adicional
Mensagem do usuário: {user_input}
Mensagens do dia: {messages_today}
LeadProfile atual: {lead_profile}
Falhas consecutivas: {consecutive_low_confidence}

Tome a decisão final. Confiança >= 0.7 para aceitar. JSON apenas."""


def format_decision_agent_prompt(
    state_agent_output: str,
    response_agent_output: str,
    message_type_agent_output: str,
    user_input: str,
    consecutive_low_confidence: int = 0,
    lead_profile: str = "",
    lead_profile_output: str = "",
    messages_today: int = 0,
) -> str:
    """Formata prompt para o DecisionAgent.

    Args:
        state_agent_output: Output do StateAgent (Agente 1)
        response_agent_output: Output do ResponseAgent (Agente 2)
        message_type_agent_output: Output do MessageTypeAgent (Agente 3)
        user_input: Mensagem original do usuário
        consecutive_low_confidence: Contador de falhas consecutivas
        lead_profile: LeadProfile atual completo
        lead_profile_output: Output do LeadProfileAgent (Agente 2-B)
        messages_today: Quantidade de mensagens trocadas hoje
    """
    return DECISION_AGENT_USER_TEMPLATE.format(
        state_agent_output=state_agent_output,
        response_agent_output=response_agent_output,
        message_type_agent_output=message_type_agent_output,
        lead_profile_output=lead_profile_output or "Nenhuma extração",
        user_input=user_input,
        consecutive_low_confidence=consecutive_low_confidence,
        lead_profile=lead_profile or "Vazio",
        messages_today=messages_today,
    )
