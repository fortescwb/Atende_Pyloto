"""Prompts do módulo AI — Pipeline de 4 Agentes.

=== PIPELINE DE 4 AGENTES ===

Sequência de processamento:
1. StateAgent (LLM #1) → identifica estado e sugere transições FSM
2. ResponseAgent (LLM #2) → gera 3 candidatos de resposta
3. MessageTypeAgent (LLM #3) → seleciona formato para candidato escolhido
4. DecisionAgent (LLM #4) → valida, escolhe candidato final, decide escalation

Arquivos:
- system_role.py: persona e regras base do assistente Otto
- state_agent_prompt.py: prompt do StateAgent
- response_agent_prompt.py: prompt do ResponseAgent
- message_type_agent_prompt.py: prompt do MessageTypeAgent
- decision_agent_prompt.py: prompt do DecisionAgent

Parsers: ai/utils/agent_parser.py
Config: config/agents/*.yaml
"""

from ai.prompts.decision_agent_prompt import (
    DECISION_AGENT_SYSTEM,
    format_decision_agent_prompt,
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
    "DECISION_AGENT_SYSTEM",
    "MESSAGE_TYPE_AGENT_SYSTEM",
    "RESPONSE_AGENT_SYSTEM",
    # Agent prompts (4-agent pipeline)
    "STATE_AGENT_SYSTEM",
    # System role
    "SYSTEM_ROLE",
    "contains_sensitive_content",
    "format_decision_agent_prompt",
    "format_message_type_agent_prompt",
    "format_response_agent_prompt",
    "format_state_agent_prompt",
    "get_expected_intents",
    "get_sensitivity_level",
    # State prompts
    "get_state_context",
    # Validation prompts
    "get_validation_context",
    "is_intent_expected",
    "requires_escalation",
]
