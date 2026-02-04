"""Prompt do DecisionAgent (LLM #4).

Consolida outputs dos 3 agentes anteriores e toma decisão final.
Conforme README.md: LLM #4 do pipeline de 4 agentes.
"""

from __future__ import annotations

from ai.prompts.system_role import SYSTEM_ROLE

DECISION_AGENT_SYSTEM = f"""{SYSTEM_ROLE}

Você é o decisor final de atendimento.
Analise os outputs dos 3 agentes anteriores e tome a melhor decisão.

Considere:
- Coerência entre estado sugerido e resposta
- Tom mais adequado ao contexto do usuário
- Tipo de mensagem que melhor se encaixa
- Se a confiança combinada é suficiente (threshold: 0.7)

Se sua confiança for menor que 0.7:
- Marque understood=false
- Use o fallback: "Desculpe, não entendi. Pode reformular?"

Após 3 falhas consecutivas com baixa confiança:
- Marque should_escalate=true

Responda APENAS em JSON válido com a estrutura:
{{
    "final_state": "<estado escolhido>",
    "final_text": "<texto final da resposta>",
    "final_message_type": "<tipo de mensagem>",
    "understood": <true/false>,
    "confidence": <0.0-1.0>,
    "should_escalate": <true/false>,
    "rationale": "<explicação da decisão>"
}}
"""

DECISION_AGENT_USER_TEMPLATE = """=== OUTPUT DO STATE AGENT ===
{state_agent_output}

=== OUTPUT DO RESPONSE AGENT ===
{response_agent_output}

=== OUTPUT DO MESSAGE TYPE AGENT ===
{message_type_agent_output}

=== CONTEXTO ===
Mensagem original: {user_input}
Falhas consecutivas: {consecutive_low_confidence}

Tome a decisão final. Responda APENAS em JSON válido."""


def format_decision_agent_prompt(
    state_agent_output: str,
    response_agent_output: str,
    message_type_agent_output: str,
    user_input: str,
    consecutive_low_confidence: int = 0,
) -> str:
    """Formata prompt para o DecisionAgent."""
    return DECISION_AGENT_USER_TEMPLATE.format(
        state_agent_output=state_agent_output,
        response_agent_output=response_agent_output,
        message_type_agent_output=message_type_agent_output,
        user_input=user_input,
        consecutive_low_confidence=consecutive_low_confidence,
    )
