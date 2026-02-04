"""Testes para ai/utils/sanitizer.py.

Valida sanitização de PII.
"""

from ai.utils.sanitizer import contains_pii, mask_history, sanitize_pii


class TestSanitizePII:
    """Testes para sanitize_pii."""

    def test_empty_string(self) -> None:
        """Valida string vazia."""
        assert sanitize_pii("") == ""

    def test_no_pii(self) -> None:
        """Valida texto sem PII."""
        text = "Olá, preciso de ajuda"
        assert sanitize_pii(text) == text

    def test_cpf_with_dots(self) -> None:
        """Valida CPF com pontuação."""
        text = "Meu CPF é 123.456.789-10"
        assert sanitize_pii(text) == "Meu CPF é [CPF]"

    def test_cpf_without_dots(self) -> None:
        """Valida CPF sem pontuação."""
        text = "CPF: 12345678910"
        assert sanitize_pii(text) == "CPF: [CPF]"

    def test_cnpj_with_dots(self) -> None:
        """Valida CNPJ com pontuação."""
        text = "CNPJ: 12.345.678/0001-90"
        assert sanitize_pii(text) == "CNPJ: [CNPJ]"

    def test_cnpj_without_dots(self) -> None:
        """Valida CNPJ sem pontuação."""
        text = "CNPJ 12345678000190"
        assert sanitize_pii(text) == "CNPJ [CNPJ]"

    def test_email(self) -> None:
        """Valida e-mail."""
        text = "Contato: usuario@exemplo.com.br"
        assert sanitize_pii(text) == "Contato: [EMAIL]"

    def test_phone_with_country_code(self) -> None:
        """Valida telefone com código de país."""
        text = "Tel: +55 11 98765-4321"
        assert sanitize_pii(text) == "Tel: [PHONE]"

    def test_phone_with_area_code(self) -> None:
        """Valida telefone com DDD."""
        text = "Ligue para (11) 98765-4321"
        assert sanitize_pii(text) == "Ligue para [PHONE]"

    def test_phone_simple(self) -> None:
        """Valida telefone simples."""
        text = "Celular: 98765-4321"
        assert sanitize_pii(text) == "Celular: [PHONE]"

    def test_multiple_pii(self) -> None:
        """Valida múltiplos PII no mesmo texto."""
        text = "CPF: 123.456.789-10, email: teste@teste.com"
        result = sanitize_pii(text)
        assert "[CPF]" in result
        assert "[EMAIL]" in result
        assert "123.456.789-10" not in result
        assert "teste@teste.com" not in result

    def test_deterministic(self) -> None:
        """Valida que resultado é determinístico."""
        text = "CPF: 123.456.789-10"
        result1 = sanitize_pii(text)
        result2 = sanitize_pii(text)
        assert result1 == result2


class TestMaskHistory:
    """Testes para mask_history."""

    def test_empty_list(self) -> None:
        """Valida lista vazia."""
        assert mask_history([]) == []

    def test_single_message(self) -> None:
        """Valida mensagem única."""
        messages = ["Meu CPF é 123.456.789-10"]
        result = mask_history(messages)
        assert result == ["Meu CPF é [CPF]"]

    def test_multiple_messages(self) -> None:
        """Valida múltiplas mensagens."""
        messages = ["Olá", "Meu email é test@test.com", "Obrigado"]
        result = mask_history(messages)
        assert len(result) == 3
        assert result[0] == "Olá"
        assert "[EMAIL]" in result[1]
        assert result[2] == "Obrigado"

    def test_truncation(self) -> None:
        """Valida truncamento para últimas N mensagens."""
        messages = [f"msg{i}" for i in range(10)]
        result = mask_history(messages, max_messages=3)
        assert len(result) == 3
        assert result == ["msg7", "msg8", "msg9"]

    def test_custom_max_messages(self) -> None:
        """Valida limite customizado."""
        messages = [f"msg{i}" for i in range(10)]
        result = mask_history(messages, max_messages=2)
        assert len(result) == 2


class TestContainsPII:
    """Testes para contains_pii."""

    def test_empty_string(self) -> None:
        """Valida string vazia."""
        assert contains_pii("") is False

    def test_no_pii(self) -> None:
        """Valida texto sem PII."""
        assert contains_pii("Olá, preciso de ajuda") is False

    def test_with_cpf(self) -> None:
        """Valida texto com CPF."""
        assert contains_pii("CPF: 123.456.789-10") is True

    def test_with_email(self) -> None:
        """Valida texto com e-mail."""
        assert contains_pii("email: test@test.com") is True

    def test_with_phone(self) -> None:
        """Valida texto com telefone."""
        assert contains_pii("Tel: +55 11 98765-4321") is True

    def test_with_cnpj(self) -> None:
        """Valida texto com CNPJ."""
        assert contains_pii("CNPJ: 12.345.678/0001-90") is True
