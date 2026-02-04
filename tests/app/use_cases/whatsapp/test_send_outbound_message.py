"""Testes para SendOutboundMessageUseCase."""

from __future__ import annotations

import pytest

from app.protocols.models import OutboundMessageRequest, OutboundMessageResponse
from app.protocols.validator import ValidationError
from app.use_cases.whatsapp.send_outbound_message import SendOutboundMessageUseCase


class FakeValidator:
    """Validator fake para testes."""

    def __init__(self, should_fail: bool = False, error_msg: str = "") -> None:
        self._should_fail = should_fail
        self._error_msg = error_msg

    def validate_outbound_request(self, request: OutboundMessageRequest) -> None:
        """Valida ou lança erro."""
        if self._should_fail:
            raise ValidationError(self._error_msg)


class FakeBuilder:
    """Builder fake para testes."""

    def __init__(self, should_fail: bool = False) -> None:
        self._should_fail = should_fail

    def build_full_payload(self, request: OutboundMessageRequest) -> dict:
        """Constrói payload fake."""
        if self._should_fail:
            raise ValueError("Build error")
        return {
            "messaging_product": "whatsapp",
            "to": request.to,
            "type": request.message_type or "text",
            "text": {"body": request.text},
        }


class FakeSender:
    """Sender fake para testes."""

    def __init__(
        self,
        success: bool = True,
        message_id: str = "wamid_123",
        error_code: str | None = None,
    ) -> None:
        self._success = success
        self._message_id = message_id
        self._error_code = error_code
        self.sent_payloads: list[dict] = []

    async def send(
        self, request: OutboundMessageRequest, payload: dict
    ) -> OutboundMessageResponse:
        """Simula envio."""
        self.sent_payloads.append(payload)
        if self._success:
            return OutboundMessageResponse(
                success=True,
                message_id=self._message_id,
                sent_at_unix=1706875200,
            )
        return OutboundMessageResponse(
            success=False,
            error_code=self._error_code or "SEND_ERROR",
            error_message="Falha no envio",
        )


@pytest.fixture
def text_request() -> OutboundMessageRequest:
    """Request de texto simples."""
    return OutboundMessageRequest(
        to="+5511999998888",
        message_type="text",
        text="Olá, tudo bem?",
        idempotency_key="idem_001",
    )


@pytest.fixture
def media_request() -> OutboundMessageRequest:
    """Request de mídia."""
    return OutboundMessageRequest(
        to="+5511999997777",
        message_type="image",
        media_id="media_abc123",
        media_mime_type="image/jpeg",
    )


class TestSendOutboundMessageUseCase:
    """Testes do use case de envio outbound."""

    @pytest.mark.asyncio
    async def test_execute_success_returns_message_id(
        self, text_request: OutboundMessageRequest
    ) -> None:
        """Envio bem-sucedido retorna message_id."""
        validator = FakeValidator()
        builder = FakeBuilder()
        sender = FakeSender(success=True, message_id="wamid_success")

        use_case = SendOutboundMessageUseCase(
            validator=validator,
            builder=builder,
            sender=sender,
        )

        result = await use_case.execute(text_request)

        assert result.success is True
        assert result.message_id == "wamid_success"
        assert result.error_code is None
        assert len(sender.sent_payloads) == 1

    @pytest.mark.asyncio
    async def test_execute_validation_error_returns_failure(
        self, text_request: OutboundMessageRequest
    ) -> None:
        """Erro de validação retorna failure."""
        validator = FakeValidator(should_fail=True, error_msg="Campo 'to' inválido")
        builder = FakeBuilder()
        sender = FakeSender()

        use_case = SendOutboundMessageUseCase(
            validator=validator,
            builder=builder,
            sender=sender,
        )

        result = await use_case.execute(text_request)

        assert result.success is False
        assert result.error_code == "VALIDATION_ERROR"
        assert "Campo 'to' inválido" in (result.error_message or "")
        assert len(sender.sent_payloads) == 0

    @pytest.mark.asyncio
    async def test_execute_builder_error_returns_failure(
        self, text_request: OutboundMessageRequest
    ) -> None:
        """Erro no builder retorna failure."""
        validator = FakeValidator()
        builder = FakeBuilder(should_fail=True)
        sender = FakeSender()

        use_case = SendOutboundMessageUseCase(
            validator=validator,
            builder=builder,
            sender=sender,
        )

        result = await use_case.execute(text_request)

        assert result.success is False
        assert result.error_code == "PAYLOAD_BUILD_ERROR"
        assert "Build error" in (result.error_message or "")
        assert len(sender.sent_payloads) == 0

    @pytest.mark.asyncio
    async def test_execute_sender_failure_returns_error(
        self, text_request: OutboundMessageRequest
    ) -> None:
        """Falha no sender retorna erro."""
        validator = FakeValidator()
        builder = FakeBuilder()
        sender = FakeSender(success=False, error_code="RATE_LIMITED")

        use_case = SendOutboundMessageUseCase(
            validator=validator,
            builder=builder,
            sender=sender,
        )

        result = await use_case.execute(text_request)

        assert result.success is False
        assert result.error_code == "RATE_LIMITED"
        assert len(sender.sent_payloads) == 1

    @pytest.mark.asyncio
    async def test_execute_media_request_builds_correctly(
        self, media_request: OutboundMessageRequest
    ) -> None:
        """Request de mídia é construída corretamente."""
        validator = FakeValidator()
        builder = FakeBuilder()
        sender = FakeSender(success=True, message_id="wamid_media")

        use_case = SendOutboundMessageUseCase(
            validator=validator,
            builder=builder,
            sender=sender,
        )

        result = await use_case.execute(media_request)

        assert result.success is True
        assert result.message_id == "wamid_media"


class TestDedupeKeyGeneration:
    """Testes de geração de chave de dedupe."""

    def test_generate_dedupe_key_returns_sha256(self) -> None:
        """Chave de dedupe é SHA256."""
        key = SendOutboundMessageUseCase.generate_dedupe_key(
            to="+5511999998888",
            message_type="text",
            content_hash="abc123",
        )

        assert len(key) == 64  # SHA256 hex
        assert key.isalnum()

    def test_generate_dedupe_key_is_deterministic(self) -> None:
        """Mesmos inputs geram mesma chave."""
        key1 = SendOutboundMessageUseCase.generate_dedupe_key(
            to="+5511999998888",
            message_type="text",
            content_hash="abc123",
        )
        key2 = SendOutboundMessageUseCase.generate_dedupe_key(
            to="+5511999998888",
            message_type="text",
            content_hash="abc123",
        )

        assert key1 == key2

    def test_generate_dedupe_key_differs_for_different_inputs(self) -> None:
        """Inputs diferentes geram chaves diferentes."""
        key1 = SendOutboundMessageUseCase.generate_dedupe_key(
            to="+5511999998888",
            message_type="text",
            content_hash="abc123",
        )
        key2 = SendOutboundMessageUseCase.generate_dedupe_key(
            to="+5511999997777",  # Número diferente
            message_type="text",
            content_hash="abc123",
        )

        assert key1 != key2


class TestHashContent:
    """Testes de hash de conteúdo."""

    def test_hash_content_returns_sha256(self) -> None:
        """Hash é SHA256."""
        payload = {"text": {"body": "Olá"}}
        content_hash = SendOutboundMessageUseCase.hash_content(payload)

        assert len(content_hash) == 64
        assert content_hash.isalnum()

    def test_hash_content_is_deterministic(self) -> None:
        """Mesmo payload gera mesmo hash."""
        payload = {"text": {"body": "Olá"}, "to": "+5511999998888"}
        hash1 = SendOutboundMessageUseCase.hash_content(payload)
        hash2 = SendOutboundMessageUseCase.hash_content(payload)

        assert hash1 == hash2

    def test_hash_content_differs_for_different_payloads(self) -> None:
        """Payloads diferentes geram hashes diferentes."""
        payload1 = {"text": {"body": "Olá"}}
        payload2 = {"text": {"body": "Tchau"}}

        hash1 = SendOutboundMessageUseCase.hash_content(payload1)
        hash2 = SendOutboundMessageUseCase.hash_content(payload2)

        assert hash1 != hash2
