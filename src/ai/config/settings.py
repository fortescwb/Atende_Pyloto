"""Configurações para o módulo de IA.

Define settings tipados para modelos, timeouts e thresholds.
Conforme REGRAS_E_PADROES.md § 2.1: ai/config contém configuração e contratos.

Arquitetura de modelos (conforme documentação oficial OpenAI):
- StateAgent (Agente 1): gpt-5-nano — seletor de estado, rápido e focado
- ResponseAgent (Agente 2): gpt-5-chat-latest — tom conversacional
- ContactCardExtractor (Agente 2-B): gpt-5-nano — extração de dados para ContactCard
- MessageTypeAgent (Agente 3): gpt-5-nano — classificação de tipo de mensagem
- DecisionAgent (Agente 4): gpt-5.1 — decisão final com contexto completo
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AgentRole(Enum):
    """Roles dos agentes no pipeline."""

    STATE = "state"  # Agente 1: Seletor de estado (gpt-5-nano)
    RESPONSE = "response"  # Agente 2: Geração de resposta (gpt-5-chat-latest)
    CONTACT_CARD_EXTRACTOR = "contact_card_extractor"  # Agente 2-B
    MESSAGE_TYPE = "message_type"  # Agente 3: Tipo de mensagem (gpt-5-nano)
    DECISION = "decision"  # Agente 4: Decisor final (gpt-5.1)


class ReasoningLevel(Enum):
    """Níveis de reasoning control para modelos."""

    NONE = "none"  # Sem reasoning explícito
    LOW = "low"  # Reasoning mínimo (padrão para FSM)
    MEDIUM = "medium"  # Reasoning moderado
    HIGH = "high"  # Reasoning profundo (não recomendado para produção)


# Nomes oficiais dos modelos OpenAI
MODEL_GPT5_NANO = "gpt-5-nano-2025-08-07"
MODEL_GPT5_1 = "gpt-5.1-2025-11-13"
MODEL_GPT5_CHAT = "gpt-5-chat-latest"


@dataclass(frozen=True, slots=True)
class AIModelSettings:
    """Configurações de modelo de IA.

    Atributos:
        model: Nome do modelo (ex: "gpt-5.1-2025-11-13", "gpt-5-chat-latest")
        temperature: Temperatura para geração (0.0-2.0)
        max_tokens: Limite de tokens na resposta
        reasoning_level: Nível de reasoning control
    """

    model: str = MODEL_GPT5_NANO
    temperature: float = 0.3
    max_tokens: int = 400
    reasoning_level: ReasoningLevel = ReasoningLevel.LOW


@dataclass(frozen=True, slots=True)
class AgentModelConfig:
    """Configuração de modelo específica por agente.

    Cada agente pode ter configuração distinta de modelo,
    temperatura e reasoning level conforme sua função.
    """

    state: AIModelSettings = field(
        default_factory=lambda: AIModelSettings(
            model=MODEL_GPT5_NANO,  # Rápido para seleção de estado
            temperature=0.1,  # Baixa para consistência
            max_tokens=100,  # Resposta curta: "Próximo estado: X, Confiança: Y"
            reasoning_level=ReasoningLevel.NONE,
        )
    )
    response: AIModelSettings = field(
        default_factory=lambda: AIModelSettings(
            model=MODEL_GPT5_CHAT,  # Chat para tom conversacional
            temperature=0.7,  # Mais criativo para resposta humana
            max_tokens=500,
            reasoning_level=ReasoningLevel.NONE,
        )
    )
    contact_card_extractor: AIModelSettings = field(
        default_factory=lambda: AIModelSettings(
            model=MODEL_GPT5_NANO,  # Nano para extração de dados
            temperature=0.1,  # Determinístico para extração precisa
            max_tokens=200,  # Dados estruturados
            reasoning_level=ReasoningLevel.NONE,
        )
    )
    message_type: AIModelSettings = field(
        default_factory=lambda: AIModelSettings(
            model=MODEL_GPT5_NANO,  # Nano para classificação pura
            temperature=0.1,  # Quase determinístico
            max_tokens=50,  # Resposta muito curta
            reasoning_level=ReasoningLevel.NONE,
        )
    )
    decision: AIModelSettings = field(
        default_factory=lambda: AIModelSettings(
            model=MODEL_GPT5_1,  # Modelo completo para decisão final
            temperature=0.2,
            max_tokens=300,
            reasoning_level=ReasoningLevel.LOW,
        )
    )

    def get_for_agent(self, role: AgentRole) -> AIModelSettings:
        """Retorna configuração para um agente específico."""
        return {
            AgentRole.STATE: self.state,
            AgentRole.RESPONSE: self.response,
            AgentRole.CONTACT_CARD_EXTRACTOR: self.contact_card_extractor,
            AgentRole.MESSAGE_TYPE: self.message_type,
            AgentRole.DECISION: self.decision,
        }[role]


@dataclass(frozen=True, slots=True)
class AITimeoutSettings:
    """Configurações de timeout para chamadas de IA.

    Atributos:
        request_timeout: Timeout por requisição em segundos
        max_retries: Número máximo de retries
    """

    request_timeout: float = 15.0
    max_retries: int = 3


@dataclass(frozen=True, slots=True)
class AIThresholdSettings:
    """Thresholds para decisões de IA.

    Atributos:
        min_confidence: Confiança mínima para aceitar resposta (0.7 padrão)
        fallback_confidence: Confiança atribuída a fallbacks
        requires_review_threshold: Abaixo deste valor, requer revisão humana
        escalate_after_consecutive: Escalar após N baixas confianças consecutivas

    ATENÇÃO — Mitigação de overconfidence:
    Monitorar se média de confiança > 0.9 por longos períodos.
    Confiança constante é sinal de problema, não de qualidade.
    """

    min_confidence: float = 0.7  # Threshold validado
    fallback_confidence: float = 0.3
    requires_review_threshold: float = 0.5
    escalate_after_consecutive: int = 3  # Conforme README


@dataclass(frozen=True, slots=True)
class AISettings:
    """Agregador de todas as configurações de IA.

    Exemplo de uso:
        settings = AISettings()
        # ou com customização por agente
        settings = AISettings(
            agents=AgentModelConfig(
                state=AIModelSettings(model="gpt-5.1", temperature=0.2),
            ),
        )
    """

    model: AIModelSettings = field(default_factory=AIModelSettings)  # Legado
    agents: AgentModelConfig = field(default_factory=AgentModelConfig)  # Novo
    timeout: AITimeoutSettings = field(default_factory=AITimeoutSettings)
    thresholds: AIThresholdSettings = field(default_factory=AIThresholdSettings)


# Settings padrão (singleton imutável)
DEFAULT_AI_SETTINGS = AISettings()


def get_ai_settings() -> AISettings:
    """Retorna configurações de IA padrão.

    Em produção, pode ser estendido para carregar de env vars.

    Returns:
        AISettings com valores padrão ou customizados.
    """
    return DEFAULT_AI_SETTINGS
