"""Prompt do MessageTypeAgent (Agente 3) — gpt-5-nano.

Classificação de tipo de mensagem WhatsApp.
Recebe: próximo estado + mensagem a enviar.
Retorna: tipo de mensagem ideal.

TIPOS:
- text: Mensagem simples
- interactive_button: Quando precisa resposta sim/não ou escolha binária
- interactive_list: Quando há lista de opções
"""

from __future__ import annotations

# Prompt minimalista para nano — classificação pura
MESSAGE_TYPE_AGENT_SYSTEM = """Classifique o tipo de mensagem WhatsApp.

TIPOS:
- text: Texto simples (padrão)
- interactive_button: Botões (máx 3) — usar para sim/não ou escolhas simples
- interactive_list: Lista (máx 10 itens) — usar quando há múltiplas opções
    Exemplo: "Sobre o que você quer falar? 1. Suporte 2. Vendas 3. Outros"

QUANDO USAR CADA:
- Pergunta aberta → text
- Sim ou não → interactive_button
- Escolha entre 2-3 opções → interactive_button
- Escolha entre 4+ opções → interactive_list
- Informação/saudação → text

Responda JSON:
{"message_type": "<tipo>", "confidence": <0.0-1.0>}
"""

MESSAGE_TYPE_AGENT_USER_TEMPLATE = """Próximo estado: {next_state}
Mensagem a enviar: {text_content}

Classifique o tipo. JSON apenas."""


def format_message_type_agent_prompt(
    text_content: str,
    options: list[str] | None = None,
    intent_type: str = "",
    user_input: str = "",
    next_state: str = "TRIAGE",
) -> str:
    """Formata prompt para o MessageTypeAgent (nano).

    Args:
        text_content: Texto da mensagem a ser enviada
        next_state: Próximo estado definido pelo StateAgent
    """
    return MESSAGE_TYPE_AGENT_USER_TEMPLATE.format(
        text_content=text_content[:200],  # Trunca para nano
        next_state=next_state,
    )
