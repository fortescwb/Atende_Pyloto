"""Testes para ai/config/settings.py.

Valida configurações de IA com valores padrão e customizados.
"""

import pytest

from ai.config.settings import (
    AIModelSettings,
    AISettings,
    AIThresholdSettings,
    AITimeoutSettings,
    get_ai_settings,
)


class TestAIModelSettings:
    """Testes para AIModelSettings."""

    def test_default_values(self) -> None:
        """Valida valores padrão do modelo."""
        settings = AIModelSettings()

        assert settings.model == "gpt-4o-mini"
        assert settings.max_tokens == 400
        assert settings.temperature == 0.3

    def test_custom_values(self) -> None:
        """Valida valores customizados."""
        settings = AIModelSettings(
            model="gpt-4",
            max_tokens=2048,
            temperature=0.5,
        )

        assert settings.model == "gpt-4"
        assert settings.max_tokens == 2048
        assert settings.temperature == 0.5

    def test_immutable(self) -> None:
        """Valida que dataclass é imutável (frozen=True)."""
        settings = AIModelSettings()

        with pytest.raises(AttributeError):
            settings.model = "outro"  # type: ignore[misc]


class TestAITimeoutSettings:
    """Testes para AITimeoutSettings."""

    def test_default_values(self) -> None:
        """Valida valores padrão de timeout."""
        settings = AITimeoutSettings()

        assert settings.request_timeout == 15.0
        assert settings.max_retries == 3

    def test_custom_values(self) -> None:
        """Valida valores customizados."""
        settings = AITimeoutSettings(
            request_timeout=30.0,
            max_retries=5,
        )

        assert settings.request_timeout == 30.0
        assert settings.max_retries == 5


class TestAIThresholdSettings:
    """Testes para AIThresholdSettings."""

    def test_default_values(self) -> None:
        """Valida valores padrão de thresholds."""
        settings = AIThresholdSettings()

        assert settings.min_confidence == 0.5
        assert settings.requires_review_threshold == 0.4
        assert settings.fallback_confidence == 0.3

    def test_custom_values(self) -> None:
        """Valida valores customizados."""
        settings = AIThresholdSettings(
            min_confidence=0.6,
            requires_review_threshold=0.8,
            fallback_confidence=0.2,
        )

        assert settings.min_confidence == 0.6
        assert settings.requires_review_threshold == 0.8
        assert settings.fallback_confidence == 0.2


class TestAISettings:
    """Testes para AISettings."""

    def test_default_values(self) -> None:
        """Valida composição padrão."""
        settings = AISettings()

        assert isinstance(settings.model, AIModelSettings)
        assert isinstance(settings.timeout, AITimeoutSettings)
        assert isinstance(settings.thresholds, AIThresholdSettings)

    def test_custom_composition(self) -> None:
        """Valida composição customizada."""
        custom_model = AIModelSettings(model="gpt-4")
        settings = AISettings(model=custom_model)

        assert settings.model.model == "gpt-4"


class TestGetAISettings:
    """Testes para função get_ai_settings."""

    def test_returns_default_settings(self) -> None:
        """Valida retorno de settings padrão."""
        settings = get_ai_settings()

        assert isinstance(settings, AISettings)
        assert settings.model.model == "gpt-4o-mini"

    def test_returns_same_instance(self) -> None:
        """Valida que retorna mesma instância (singleton)."""
        settings1 = get_ai_settings()
        settings2 = get_ai_settings()

        assert settings1 is settings2
