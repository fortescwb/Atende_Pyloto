"""Prompts do módulo AI — Pipeline de 5 Agentes.

=== PIPELINE DE AGENTES ===

Sequência de processamento:
1. StateAgent (Agente 1) → seleciona próximo estado
2. ResponseAgent (Agente 2) → gera resposta conversacional
2-B. ContactCardExtractor (Agente 2-B) → extrai dados para ContactCard
3. MessageTypeAgent (Agente 3) → seleciona tipo de mensagem
4. DecisionAgent (Agente 4) → decisão final com confiança >= 0.7

Arquivos:
- system_role.py: persona base do assistente Otto
- state_agent_prompt.py: prompt do StateAgent
- response_agent_prompt.py: prompt do ResponseAgent
- contact_card_extractor_prompt.py: prompt do ContactCardExtractor
- message_type_agent_prompt.py: prompt do MessageTypeAgent
- decision_agent_prompt.py: prompt do DecisionAgent
"""

from ai.prompts.contact_card_extractor_prompt import (
    CONTACT_CARD_EXTRACTOR_SYSTEM,
    format_contact_card_extractor_prompt,
)
from ai.prompts.decision_agent_prompt import (
    DECISION_AGENT_SYSTEM,
    format_decision_agent_prompt,
)
from ai.prompts.message_type_agent_prompt import (
    MESSAGE_TYPE_AGENT_SYSTEM,
    format_message_type_agent_prompt,
)
from ai.prompts.otto_prompt import OTTO_SYSTEM_PROMPT, format_otto_prompt
from ai.prompts.response_agent_prompt import (
    RESPONSE_AGENT_SYSTEM,
    format_response_agent_prompt,
)
from ai.prompts.state_agent_prompt import (
    STATE_AGENT_SYSTEM,
    format_state_agent_prompt,
)
from ai.prompts.state_prompts import (
    get_expected_intents,
    get_state_context,
    is_intent_expected,
)
from ai.prompts.system_role import SYSTEM_ROLE
from ai.prompts.validation_prompts import (
    contains_sensitive_content,
    get_sensitivity_level,
    get_validation_context,
    requires_escalation,
)

__all__ = [
    "CONTACT_CARD_EXTRACTOR_SYSTEM",
    "DECISION_AGENT_SYSTEM",
    "MESSAGE_TYPE_AGENT_SYSTEM",
    "OTTO_SYSTEM_PROMPT",
    "RESPONSE_AGENT_SYSTEM",
    "STATE_AGENT_SYSTEM",
    "SYSTEM_ROLE",
    "contains_sensitive_content",
    "format_contact_card_extractor_prompt",
    "format_decision_agent_prompt",
    "format_message_type_agent_prompt",
    "format_otto_prompt",
    "format_response_agent_prompt",
    "format_state_agent_prompt",
    "get_expected_intents",
    "get_sensitivity_level",
    "get_state_context",
    "get_validation_context",
    "is_intent_expected",
    "requires_escalation",
]
