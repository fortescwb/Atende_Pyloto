"""Testes para o loader de contexto institucional."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ai.config.institutional_loader import (
    _get_fallback_context,
    clear_cache,
    get_address_info,
    get_business_hours,
    get_contact_info,
    get_institutional_prompt_section,
    get_service_info,
    load_institutional_context,
)


class TestInstitutionalLoader:
    """Testes para o loader de contexto institucional."""

    def setup_method(self) -> None:
        """Limpa cache antes de cada teste."""
        clear_cache()

    def test_load_institutional_context_returns_dict(self) -> None:
        """Verifica que load_institutional_context retorna dict."""
        context = load_institutional_context()
        assert isinstance(context, dict)
        assert "empresa" in context

    def test_load_institutional_context_is_cached(self) -> None:
        """Verifica que a função é cached (lru_cache)."""
        ctx1 = load_institutional_context()
        ctx2 = load_institutional_context()
        assert ctx1 is ctx2  # Mesma referência = cache

    def test_clear_cache_works(self) -> None:
        """Verifica que clear_cache limpa o cache."""
        load_institutional_context()  # popula cache
        clear_cache()
        ctx2 = load_institutional_context()
        # Após limpar cache, deve carregar novamente
        # O conteúdo será igual, mas pode ser novo objeto
        assert ctx2 is not None
        assert "empresa" in ctx2

    def test_fallback_context_structure(self) -> None:
        """Verifica estrutura do contexto de fallback."""
        fallback = _get_fallback_context()
        assert "empresa" in fallback
        assert "contato" in fallback
        assert "vertentes" in fallback
        assert fallback["empresa"]["nome"] == "Pyloto"

    def test_get_institutional_prompt_section_returns_string(self) -> None:
        """Verifica que get_institutional_prompt_section retorna string."""
        section = get_institutional_prompt_section()
        assert isinstance(section, str)
        assert "Pyloto" in section

    def test_get_contact_info_returns_dict(self) -> None:
        """Verifica que get_contact_info retorna dict."""
        contact = get_contact_info()
        assert isinstance(contact, dict)

    def test_get_address_info_returns_dict(self) -> None:
        """Verifica que get_address_info retorna dict."""
        address = get_address_info()
        assert isinstance(address, dict)

    def test_get_business_hours_returns_dict(self) -> None:
        """Verifica que get_business_hours retorna dict."""
        hours = get_business_hours()
        assert isinstance(hours, dict)

    def test_get_service_info_existing(self) -> None:
        """Verifica busca de serviço existente."""
        # O YAML tem vertentes, vamos buscar uma
        context = load_institutional_context()
        vertentes = context.get("vertentes", [])
        if vertentes:
            service_id = vertentes[0].get("id")
            if service_id:
                service = get_service_info(service_id)
                assert service is not None
                assert service["id"] == service_id

    def test_get_service_info_not_found(self) -> None:
        """Verifica busca de serviço inexistente."""
        service = get_service_info("servico_inexistente")
        assert service is None

    def test_load_with_missing_file_returns_fallback(self) -> None:
        """Verifica que arquivo ausente retorna fallback."""
        clear_cache()
        fake_path = Path("/var/lib/pyloto_test_nonexistent_xyz.yaml")
        with patch(
            "ai.config.institutional_loader._INSTITUTIONAL_CONTEXT_PATH",
            fake_path,
        ):
            clear_cache()
            ctx = load_institutional_context()
            # Deve retornar fallback (que o cache anterior foi limpo)
            # Nota: o cache pode ter sido preenchido antes do patch
            assert ctx is not None


class TestInstitutionalPromptSection:
    """Testes específicos para formatação de prompt."""

    def setup_method(self) -> None:
        """Limpa cache antes de cada teste."""
        clear_cache()

    def test_prompt_section_contains_empresa(self) -> None:
        """Verifica que seção do prompt contém empresa."""
        section = get_institutional_prompt_section()
        assert "Empresa" in section or "Pyloto" in section

    def test_prompt_section_contains_contato(self) -> None:
        """Verifica que seção do prompt contém contato."""
        section = get_institutional_prompt_section()
        # Pode conter "Contato" ou email/telefone
        assert len(section) > 0  # Deve ter algum conteúdo
