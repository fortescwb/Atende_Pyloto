"""Testes para ai/config/agent_config.py."""

import pytest

from ai.config.agent_config import AgentConfig, get_all_agent_configs, load_agent_config


class TestLoadAgentConfig:
    """Testes para load_agent_config."""

    def test_load_state_agent(self) -> None:
        """Testa carregamento do state_agent.yaml."""
        config = load_agent_config("state_agent")
        assert config.agent_name == "state_agent"
        assert config.model_name == "gpt-4o-mini"
        assert 0.0 <= config.temperature <= 1.0

    def test_load_response_agent(self) -> None:
        """Testa carregamento do response_agent.yaml."""
        config = load_agent_config("response_agent")
        assert config.agent_name == "response_agent"
        assert config.max_tokens > 0

    def test_load_decision_agent(self) -> None:
        """Testa carregamento do decision_agent.yaml."""
        config = load_agent_config("decision_agent")
        assert config.agent_name == "decision_agent"
        assert config.timeout_seconds > 0

    def test_nonexistent_raises_file_not_found(self) -> None:
        """Testa que agente inexistente levanta FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_agent_config("nonexistent_agent")

    def test_config_is_cached(self) -> None:
        """Testa que config é cacheada."""
        config1 = load_agent_config("state_agent")
        config2 = load_agent_config("state_agent")
        assert config1 is config2


class TestGetAllAgentConfigs:
    """Testes para get_all_agent_configs."""

    def test_returns_all_four_agents(self) -> None:
        """Testa que retorna 4 agentes."""
        configs = get_all_agent_configs()
        assert len(configs) == 4
        assert "state_agent" in configs
        assert "response_agent" in configs
        assert "message_type_agent" in configs
        assert "decision_agent" in configs

    def test_all_configs_are_valid(self) -> None:
        """Testa que todas configs são instâncias válidas."""
        configs = get_all_agent_configs()
        for name, config in configs.items():
            assert isinstance(config, AgentConfig)
            assert config.agent_name == name
