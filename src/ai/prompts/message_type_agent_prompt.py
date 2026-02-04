"""Prompt do MessageTypeAgent (LLM #3).

Seleciona o tipo de mensagem WhatsApp mais adequado.
Conforme README.md: LLM #3 do pipeline de 4 agentes.
"""

from __future__ import annotations

from ai.prompts.system_role import SYSTEM_ROLE

MESSAGE_TYPE_AGENT_SYSTEM = f"""{SYSTEM_ROLE}

Você seleciona o tipo de mensagem mais adequado para WhatsApp.

Tipos disponíveis:
- text: Mensagem de texto simples (até 4096 chars)
- interactive_button: Mensagem com até 3 botões de ação
- interactive_list: Mensagem com lista (até 10 itens)
- template: Template pré-aprovado (mensagens proativas)
- reaction: Apenas reação emoji (quando não precisa responder)

Regras para "reaction":
- Use APENAS quando a mensagem do usuário não requer resposta textual
- Exemplos: "ok", "blz", "obrigado", "valeu", "👍"

Responda APENAS em JSON válido com a estrutura:
{{
    "message_type": "<tipo>",
    "parameters": {{}},
    "confidence": <0.0-1.0>,
    "rationale": "<explicação>"
}}
"""

MESSAGE_TYPE_AGENT_USER_TEMPLATE = """Resposta a enviar: {text_content}

Opções disponíveis: {options}
Tipo de intent: {intent_type}
Mensagem original do usuário: {user_input}

Selecione o melhor tipo. Responda APENAS em JSON válido."""


def format_message_type_agent_prompt(
    text_content: str,
    options: list[str] | None = None,
    intent_type: str = "",
    user_input: str = "",
) -> str:
    """Formata prompt para o MessageTypeAgent."""
    return MESSAGE_TYPE_AGENT_USER_TEMPLATE.format(
        text_content=text_content,
        options=", ".join(options) if options else "Nenhuma opção",
        intent_type=intent_type or "Não especificado",
        user_input=user_input,
    )
