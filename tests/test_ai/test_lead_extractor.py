"""Testes para o LeadExtractor."""

from __future__ import annotations

from ai.services.lead_extractor import (
    ExtractedLeadData,
    extract_email,
    extract_from_history,
    extract_lead_data,
    extract_name,
    extract_phone,
    merge_lead_data,
)


class TestExtractEmail:
    """Testes para extração de email."""

    def test_extract_simple_email(self) -> None:
        """Extrai email simples."""
        result = extract_email("meu email é joao@exemplo.com.br")
        assert result == "joao@exemplo.com.br"

    def test_extract_email_uppercase(self) -> None:
        """Normaliza email para lowercase."""
        result = extract_email("Email: MARIA@Empresa.COM")
        assert result == "maria@empresa.com"

    def test_no_email_returns_none(self) -> None:
        """Retorna None quando não há email."""
        result = extract_email("não tenho email")
        assert result is None

    def test_extract_first_email(self) -> None:
        """Extrai apenas primeiro email."""
        result = extract_email("emails: a@b.com e c@d.com")
        assert result == "a@b.com"


class TestExtractPhone:
    """Testes para extração de telefone."""

    def test_extract_phone_with_ddd(self) -> None:
        """Extrai telefone com DDD."""
        result = extract_phone("meu telefone é (11) 99999-8888")
        assert result == "11999998888"

    def test_extract_phone_international(self) -> None:
        """Extrai telefone com código de país."""
        result = extract_phone("+55 11 99999-8888")
        assert result == "5511999998888"

    def test_extract_phone_simple(self) -> None:
        """Extrai telefone simples."""
        result = extract_phone("liga pra 999998888")
        assert result == "999998888"

    def test_no_phone_returns_none(self) -> None:
        """Retorna None quando não há telefone."""
        result = extract_phone("não tenho telefone")
        assert result is None

    def test_invalid_short_phone(self) -> None:
        """Rejeita telefone muito curto."""
        result = extract_phone("o número é 1234")
        assert result is None


class TestExtractName:
    """Testes para extração de nome."""

    def test_extract_name_meu_nome_e(self) -> None:
        """Extrai nome de 'meu nome é X'."""
        result = extract_name("meu nome é João Silva")
        assert result == "João Silva"

    def test_extract_name_me_chamo(self) -> None:
        """Extrai nome de 'me chamo X'."""
        result = extract_name("me chamo Maria")
        assert result == "Maria"

    def test_extract_name_sou_o(self) -> None:
        """Extrai nome de 'sou o X'."""
        result = extract_name("sou o Carlos")
        assert result == "Carlos"

    def test_extract_name_sou_a(self) -> None:
        """Extrai nome de 'sou a X'."""
        result = extract_name("sou a Ana Paula")
        assert result == "Ana Paula"

    def test_no_name_returns_none(self) -> None:
        """Retorna None quando nome não é mencionado."""
        result = extract_name("oi, tudo bem?")
        assert result is None

    def test_name_normalized_to_title(self) -> None:
        """Nome é normalizado para Title Case."""
        result = extract_name("meu nome é PEDRO")
        assert result == "Pedro"


class TestExtractLeadData:
    """Testes para extração combinada."""

    def test_extract_all_data(self) -> None:
        """Extrai todos os dados de uma mensagem."""
        text = "meu nome é José, email jose@email.com, tel (11) 98765-4321"
        result = extract_lead_data(text)

        assert result.name == "José"
        assert result.email == "jose@email.com"
        assert result.phone == "11987654321"

    def test_extract_partial_data(self) -> None:
        """Extrai dados parciais."""
        text = "pode me ligar em 99999-8888"
        result = extract_lead_data(text)

        assert result.name is None
        assert result.email is None
        assert result.phone == "999998888"

    def test_extract_no_data(self) -> None:
        """Retorna dados vazios se nada encontrado."""
        result = extract_lead_data("oi, tudo bem?")

        assert result.name is None
        assert result.email is None
        assert result.phone is None


class TestMergeLeadData:
    """Testes para mesclagem de dados."""

    def test_merge_with_none(self) -> None:
        """Mesclar com None retorna novo."""
        new = ExtractedLeadData(name="João")
        result = merge_lead_data(None, new)
        assert result.name == "João"

    def test_merge_new_overwrites(self) -> None:
        """Novos dados sobrescrevem existentes."""
        existing = ExtractedLeadData(name="João", email="joao@a.com")
        new = ExtractedLeadData(email="joao@b.com")

        result = merge_lead_data(existing, new)

        assert result.name == "João"  # mantido
        assert result.email == "joao@b.com"  # atualizado

    def test_merge_preserves_existing(self) -> None:
        """Dados existentes são preservados se novos são None."""
        existing = ExtractedLeadData(name="Maria", phone="11999998888")
        new = ExtractedLeadData()

        result = merge_lead_data(existing, new)

        assert result.name == "Maria"
        assert result.phone == "11999998888"


class TestExtractFromHistory:
    """Testes para extração de histórico."""

    def test_extract_from_multiple_messages(self) -> None:
        """Extrai dados de múltiplas mensagens."""
        messages = [
            "oi, tudo bem?",
            "meu nome é Pedro",
            "meu email é pedro@email.com",
            "telefone (21) 98765-4321",
        ]

        result = extract_from_history(messages)

        assert result.name == "Pedro"
        assert result.email == "pedro@email.com"
        assert result.phone == "21987654321"

    def test_extract_from_empty_history(self) -> None:
        """Retorna dados vazios para histórico vazio."""
        result = extract_from_history([])

        assert result.name is None
        assert result.email is None
        assert result.phone is None

    def test_later_messages_overwrite(self) -> None:
        """Mensagens mais recentes sobrescrevem anteriores."""
        messages = [
            "meu email é antigo@email.com",
            "ops, meu email correto é novo@email.com",
        ]

        result = extract_from_history(messages)

        assert result.email == "novo@email.com"
