"""Prompts do módulo AI — Pipeline de 5 Agentes.

=== PIPELINE DE AGENTES ===

Sequência de processamento:
1. StateAgent (Agente 1) → seleciona próximo estado
2. ResponseAgent (Agente 2) → gera resposta conversacional
2-B. LeadProfileAgent (Agente 2-B) → extrai dados para LeadProfile
3. MessageTypeAgent (Agente 3) → seleciona tipo de mensagem
4. DecisionAgent (Agente 4) → decisão final com confiança >= 0.7

Arquivos:
- system_role.py: persona base do assistente Otto
- state_agent_prompt.py: prompt do StateAgent
- response_agent_prompt.py: prompt do ResponseAgent
- lead_profile_agent_prompt.py: prompt do LeadProfileAgent (NOVO)
- message_type_agent_prompt.py: prompt do MessageTypeAgent
- decision_agent_prompt.py: prompt do DecisionAgent
"""

from ai.prompts.decision_agent_prompt import (
    DECISION_AGENT_SYSTEM,
    format_decision_agent_prompt,
)
from ai.prompts.lead_profile_agent_prompt import (
    LEAD_PROFILE_AGENT_SYSTEM,
    format_lead_profile_agent_prompt,
)
from ai.prompts.message_type_agent_prompt import (
    MESSAGE_TYPE_AGENT_SYSTEM,
    format_message_type_agent_prompt,
)
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
    # Agent system prompts
    "DECISION_AGENT_SYSTEM",
    "LEAD_PROFILE_AGENT_SYSTEM",
    "MESSAGE_TYPE_AGENT_SYSTEM",
    "RESPONSE_AGENT_SYSTEM",
    "STATE_AGENT_SYSTEM",
    # System role
    "SYSTEM_ROLE",
    # Agent prompt formatters
    "format_decision_agent_prompt",
    "format_lead_profile_agent_prompt",
    "format_message_type_agent_prompt",
    "format_response_agent_prompt",
    "format_state_agent_prompt",
    # State prompts
    "get_expected_intents",
    "get_state_context",
    "is_intent_expected",
    # Validation prompts
    "contains_sensitive_content",
    "get_sensitivity_level",
    "get_validation_context",
    "requires_escalation",
]
