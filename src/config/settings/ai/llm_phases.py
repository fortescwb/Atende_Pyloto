"""Settings de fases LLM.

Configurações para State Selector, Response Generator e Master Decider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

AuditBackend = Literal["memory", "firestore"]


@dataclass(frozen=True)
class StateSelectorSettings:
    """Configurações do State Selector (classificador de estado).

    Attributes:
        model: Modelo LLM para classificação
        confidence_threshold: Limiar mínimo de confiança (0-1)
        max_tokens: Máximo de tokens na resposta
    """

    model: str = "gpt-4o-mini"
    confidence_threshold: float = 0.7
    max_tokens: int = 100

    def validate(self) -> list[str]:
        """Valida configurações do state selector.

        Returns:
            Lista de erros de validação.
        """
        errors: list[str] = []

        if not 0 < self.confidence_threshold <= 1:
            errors.append("STATE_SELECTOR_CONFIDENCE_THRESHOLD deve estar entre 0 e 1")

        if self.max_tokens < 1:
            errors.append("STATE_SELECTOR_MAX_TOKENS deve ser >= 1")

        return errors


@dataclass(frozen=True)
class ResponseGeneratorSettings:
    """Configurações do Response Generator.

    Attributes:
        model: Modelo LLM para geração
        min_responses: Mínimo de respostas candidatas
        max_tokens: Máximo de tokens na resposta
        temperature: Temperatura para geração
    """

    model: str = "gpt-4o-mini"
    min_responses: int = 3
    max_tokens: int = 500
    temperature: float = 0.7

    def validate(self) -> list[str]:
        """Valida configurações do response generator.

        Returns:
            Lista de erros de validação.
        """
        errors: list[str] = []

        if self.min_responses < 3:
            errors.append("RESPONSE_GENERATOR_MIN_RESPONSES deve ser >= 3")

        if self.max_tokens < 1:
            errors.append("RESPONSE_GENERATOR_MAX_TOKENS deve ser >= 1")

        if not 0 <= self.temperature <= 2:
            errors.append("RESPONSE_GENERATOR_TEMPERATURE deve estar entre 0 e 2")

        return errors


@dataclass(frozen=True)
class MasterDeciderSettings:
    """Configurações do Master Decider.

    Attributes:
        model: Modelo LLM para decisão
        confidence_threshold: Limiar mínimo de confiança
        enabled: Se master decider está habilitado
        audit_backend: Backend para auditoria de decisões
    """

    model: str = "gpt-4o-mini"
    confidence_threshold: float = 0.8
    enabled: bool = True
    audit_backend: AuditBackend = "memory"

    def validate(self, gcp_project: str, is_development: bool) -> list[str]:
        """Valida configurações do master decider.

        Args:
            gcp_project: Projeto GCP para validar firestore.
            is_development: Se está em desenvolvimento.

        Returns:
            Lista de erros de validação.
        """
        errors: list[str] = []

        if not 0 < self.confidence_threshold <= 1:
            errors.append("MASTER_DECIDER_CONFIDENCE_THRESHOLD deve estar entre 0 e 1")

        valid_backends = {"memory", "firestore"}
        if self.audit_backend not in valid_backends:
            errors.append(f"DECISION_AUDIT_BACKEND inválido: {self.audit_backend}")

        if self.audit_backend == "memory" and not is_development:
            errors.append("DECISION_AUDIT_BACKEND=memory proibido em staging/production")

        if self.enabled and self.audit_backend == "firestore" and not gcp_project:
            errors.append("DECISION_AUDIT_BACKEND=firestore requer GCP_PROJECT")

        return errors


def _load_state_selector_from_env() -> StateSelectorSettings:
    """Carrega StateSelectorSettings de variáveis de ambiente."""
    return StateSelectorSettings(
        model=os.getenv("STATE_SELECTOR_MODEL", "gpt-4o-mini"),
        confidence_threshold=float(
            os.getenv("STATE_SELECTOR_CONFIDENCE_THRESHOLD", "0.7")
        ),
        max_tokens=int(os.getenv("STATE_SELECTOR_MAX_TOKENS", "100")),
    )


def _load_response_generator_from_env() -> ResponseGeneratorSettings:
    """Carrega ResponseGeneratorSettings de variáveis de ambiente."""
    return ResponseGeneratorSettings(
        model=os.getenv("RESPONSE_GENERATOR_MODEL", "gpt-4o-mini"),
        min_responses=int(os.getenv("RESPONSE_GENERATOR_MIN_RESPONSES", "3")),
        max_tokens=int(os.getenv("RESPONSE_GENERATOR_MAX_TOKENS", "500")),
        temperature=float(os.getenv("RESPONSE_GENERATOR_TEMPERATURE", "0.7")),
    )


def _load_master_decider_from_env() -> MasterDeciderSettings:
    """Carrega MasterDeciderSettings de variáveis de ambiente."""
    backend_str = os.getenv("DECISION_AUDIT_BACKEND", "memory").lower()
    backend: AuditBackend = backend_str if backend_str == "firestore" else "memory"

    return MasterDeciderSettings(
        model=os.getenv("MASTER_DECIDER_MODEL", "gpt-4o-mini"),
        confidence_threshold=float(
            os.getenv("MASTER_DECIDER_CONFIDENCE_THRESHOLD", "0.8")
        ),
        enabled=os.getenv("MASTER_DECIDER_ENABLED", "true").lower() in ("true", "1"),
        audit_backend=backend,
    )


@lru_cache(maxsize=1)
def get_state_selector_settings() -> StateSelectorSettings:
    """Retorna instância cacheada de StateSelectorSettings."""
    return _load_state_selector_from_env()


@lru_cache(maxsize=1)
def get_response_generator_settings() -> ResponseGeneratorSettings:
    """Retorna instância cacheada de ResponseGeneratorSettings."""
    return _load_response_generator_from_env()


@lru_cache(maxsize=1)
def get_master_decider_settings() -> MasterDeciderSettings:
    """Retorna instância cacheada de MasterDeciderSettings."""
    return _load_master_decider_from_env()
