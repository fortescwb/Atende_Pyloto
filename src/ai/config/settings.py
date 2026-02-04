"""Configurações para o módulo de IA.

Define settings tipados para modelos, timeouts e thresholds.
Conforme REGRAS_E_PADROES.md § 2.1: ai/config contém configuração e contratos.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AIModelSettings:
    """Configurações de modelo de IA.

    Atributos:
        model: Nome do modelo (ex: "gpt-4o-mini")
        temperature: Temperatura para geração (0.0-2.0)
        max_tokens: Limite de tokens na resposta
    """

    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 400


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
        min_confidence: Confiança mínima para aceitar resposta
        fallback_confidence: Confiança atribuída a fallbacks
        requires_review_threshold: Abaixo deste valor, requer revisão humana
    """

    min_confidence: float = 0.5
    fallback_confidence: float = 0.3
    requires_review_threshold: float = 0.4


@dataclass(frozen=True, slots=True)
class AISettings:
    """Agregador de todas as configurações de IA.

    Exemplo de uso:
        settings = AISettings()
        # ou com customização
        settings = AISettings(
            model=AIModelSettings(model="gpt-4o"),
            timeout=AITimeoutSettings(request_timeout=30.0),
        )
    """

    model: AIModelSettings = field(default_factory=AIModelSettings)
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
