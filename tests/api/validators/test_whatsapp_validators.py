"""
Testes abrangentes para api/validators/whatsapp.

Seguindo REGRAS_E_PADROES.md § 8.1:
- Testamos comportamento e contrato público
- Um teste cobre múltiplos componentes relacionados
- Foco em cenários válidos + inválidos + bordas
"""

import pytest

from api.validators.whatsapp import (
    ValidationError as ReexportedValidationError,
)
from api.validators.whatsapp import (
    WhatsAppMessageValidator as ReexportedValidator,
)

# Imports dos validadores
from api.validators.whatsapp.errors import ValidationError
from api.validators.whatsapp.interactive import (
    _validate_button,
    _validate_cta_url,
    _validate_flow,
    _validate_list,
    _validate_location_request,
    validate_interactive_message,
)
from api.validators.whatsapp.limits import (
    MAX_BUTTON_TEXT_LENGTH,
    MAX_BUTTONS_PER_MESSAGE,
    MAX_CAPTION_LENGTH,
    MAX_FILE_SIZE_MB,
    MAX_IDEMPOTENCY_KEY_LENGTH,
    MAX_LIST_ITEMS,
    MAX_TEMPLATE_NAME_LENGTH,
    MAX_TEXT_LENGTH,
    SUPPORTED_AUDIO_TYPES,
    SUPPORTED_DOCUMENT_TYPES,
    SUPPORTED_IMAGE_TYPES,
    SUPPORTED_VIDEO_TYPES,
)
from api.validators.whatsapp.media import validate_media_message
from api.validators.whatsapp.template import (
    validate_address_message,
    validate_contacts_message,
    validate_location_message,
    validate_reaction_message,
    validate_template_message,
)
from api.validators.whatsapp.text import validate_text_message
from api.validators.whatsapp.validator_dispatcher import WhatsAppMessageValidator
from app.constants.whatsapp import MessageType

# Models
from app.protocols.models import OutboundMessageRequest


class TestValidationErrorAndLimits:
    """Testa ValidationError e constantes de limites."""

    def test_validation_error_is_exception_and_limits_are_defined(self) -> None:
        """Verifica ValidationError e todas as constantes de limites."""
        # ValidationError é Exception
        assert issubclass(ValidationError, Exception)

        # Reexport funciona
        assert ValidationError is ReexportedValidationError

        # Limites estão definidos com valores razoáveis
        assert MAX_TEXT_LENGTH == 4096
        assert MAX_CAPTION_LENGTH == 1024
        assert MAX_BUTTON_TEXT_LENGTH == 20
        assert MAX_LIST_ITEMS == 10
        assert MAX_BUTTONS_PER_MESSAGE == 3
        assert MAX_FILE_SIZE_MB == 100
        assert MAX_TEMPLATE_NAME_LENGTH == 512
        assert MAX_IDEMPOTENCY_KEY_LENGTH == 255

        # MIME types estão definidos
        assert "image/jpeg" in SUPPORTED_IMAGE_TYPES
        assert "image/png" in SUPPORTED_IMAGE_TYPES
        assert "video/mp4" in SUPPORTED_VIDEO_TYPES
        assert "audio/aac" in SUPPORTED_AUDIO_TYPES
        assert "application/pdf" in SUPPORTED_DOCUMENT_TYPES


class TestTextMessageValidation:
    """Testa validação de mensagens de texto."""

    def test_valid_text_message(self) -> None:
        """Testa texto válido."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="text",
            text="Olá, como posso ajudar?",
        )
        # Não deve lançar exceção
        validate_text_message(request)

    def test_text_message_requires_text(self) -> None:
        """Testa texto ausente."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="text",
            text=None,
        )
        with pytest.raises(ValidationError, match="text is required"):
            validate_text_message(request)

    def test_text_message_exceeds_max_length(self) -> None:
        """Testa texto muito longo."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="text",
            text="x" * (MAX_TEXT_LENGTH + 1),
        )
        with pytest.raises(ValidationError, match="exceeds maximum length"):
            validate_text_message(request)

    def test_text_message_at_max_length(self) -> None:
        """Testa texto exatamente no limite."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="text",
            text="x" * MAX_TEXT_LENGTH,
        )
        # Não deve lançar exceção
        validate_text_message(request)


class TestMediaMessageValidation:
    """Testa validação de mensagens de mídia."""

    def test_valid_image_with_media_id(self) -> None:
        """Testa imagem válida com media_id."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="image",
            media_id="1234567890",
        )
        validate_media_message(request, MessageType.IMAGE)

    def test_valid_video_with_media_url(self) -> None:
        """Testa vídeo válido com media_url."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="video",
            media_url="https://example.com/video.mp4",
        )
        validate_media_message(request, MessageType.VIDEO)

    def test_media_requires_id_or_url(self) -> None:
        """Testa mídia sem id nem url."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="image",
        )
        with pytest.raises(ValidationError, match="requires either media_id or media_url"):
            validate_media_message(request, MessageType.IMAGE)

    def test_media_caption_too_long(self) -> None:
        """Testa caption muito longo."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="image",
            media_id="123",
            text="x" * (MAX_CAPTION_LENGTH + 1),
        )
        with pytest.raises(ValidationError, match="caption/text exceeds"):
            validate_media_message(request, MessageType.IMAGE)

    def test_audio_does_not_support_caption_check(self) -> None:
        """Audio não valida caption (não suportado)."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="audio",
            media_id="123",
            text="x" * (MAX_CAPTION_LENGTH + 100),  # Muito longo mas não valida
        )
        # Audio não está em _TYPES_WITH_CAPTION, então não falha
        validate_media_message(request, MessageType.AUDIO)

    def test_valid_mime_type(self) -> None:
        """Testa MIME type válido."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="image",
            media_id="123",
            media_mime_type="image/jpeg",
        )
        validate_media_message(request, MessageType.IMAGE)


class TestInteractiveMessageValidation:
    """Testa validação de mensagens interativas."""

    def test_interactive_requires_type(self) -> None:
        """Testa tipo interativo ausente."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="interactive",
            text="Escolha uma opção",
        )
        with pytest.raises(ValidationError, match="interactive_type is required"):
            validate_interactive_message(request)

    def test_interactive_invalid_type(self) -> None:
        """Testa tipo interativo inválido."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="interactive",
            interactive_type="invalid_type",
            text="Escolha",
        )
        with pytest.raises(ValidationError, match="Invalid interactive_type"):
            validate_interactive_message(request)

    def test_interactive_requires_text(self) -> None:
        """Testa body ausente."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="interactive",
            interactive_type="button",
        )
        with pytest.raises(ValidationError, match="text.*required"):
            validate_interactive_message(request)

    def test_button_interactive_valid(self) -> None:
        """Testa botão válido."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="interactive",
            interactive_type="button",
            text="Escolha uma opção",
            buttons=[
                {"id": "btn1", "title": "Opção 1"},
                {"id": "btn2", "title": "Opção 2"},
            ],
        )
        validate_interactive_message(request)

    def test_button_requires_buttons(self) -> None:
        """Testa botão sem buttons."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="interactive",
            interactive_type="button",
            text="Escolha",
            buttons=None,
        )
        with pytest.raises(ValidationError, match="buttons is required"):
            _validate_button(request)

    def test_button_exceeds_max_count(self) -> None:
        """Testa mais botões que o permitido."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="interactive",
            interactive_type="button",
            text="Escolha",
            buttons=[{"id": f"btn{i}", "title": f"Op {i}"} for i in range(5)],
        )
        with pytest.raises(ValidationError, match="Maximum.*buttons allowed"):
            _validate_button(request)

    def test_button_invalid_structure(self) -> None:
        """Testa botão com estrutura inválida."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="interactive",
            interactive_type="button",
            text="Escolha",
            buttons=[{"id": "btn1"}],  # Falta title
        )
        with pytest.raises(ValidationError, match="must have 'id' and 'title'"):
            _validate_button(request)

    def test_button_title_too_long(self) -> None:
        """Testa título de botão muito longo."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="interactive",
            interactive_type="button",
            text="Escolha",
            buttons=[{"id": "btn1", "title": "x" * (MAX_BUTTON_TEXT_LENGTH + 1)}],
        )
        with pytest.raises(ValidationError, match="title exceeds"):
            _validate_button(request)

    def test_list_requires_sections(self) -> None:
        """Testa lista sem seções."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="interactive",
            interactive_type="list",
            text="Escolha",
            buttons=[],
        )
        with pytest.raises(ValidationError, match="At least one list section"):
            _validate_list(request)

    def test_flow_requires_all_fields(self) -> None:
        """Testa flow sem campos obrigatórios."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="interactive",
            interactive_type="flow",
            text="Preencha o formulário",
        )
        with pytest.raises(ValidationError, match="flow_id.*required"):
            _validate_flow(request)

    def test_flow_valid(self) -> None:
        """Testa flow válido."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="interactive",
            interactive_type="flow",
            text="Preencha",
            flow_id="123",
            flow_message_version="3",
            flow_token="abc",
            flow_cta="Iniciar",
            flow_action="navigate",
        )
        _validate_flow(request)

    def test_cta_url_requires_url_and_text(self) -> None:
        """Testa CTA_URL sem url."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="interactive",
            interactive_type="cta_url",
            text="Acesse nosso site",
        )
        with pytest.raises(ValidationError, match="cta_url is required"):
            _validate_cta_url(request)

    def test_cta_url_no_buttons_allowed(self) -> None:
        """Testa CTA_URL com buttons."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="interactive",
            interactive_type="cta_url",
            text="Acesse",
            cta_url="https://example.com",
            cta_display_text="Acessar",
            buttons=[{"id": "btn"}],
        )
        with pytest.raises(ValidationError, match="buttons not allowed"):
            _validate_cta_url(request)

    def test_location_request_no_buttons(self) -> None:
        """Testa location request com buttons."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="interactive",
            interactive_type="location_request_message",
            text="Compartilhe sua localização",
            buttons=[{"id": "btn"}],
        )
        with pytest.raises(ValidationError, match="buttons not allowed"):
            _validate_location_request(request)


class TestTemplateAndOtherValidation:
    """Testa validação de template, location, address, etc."""

    def test_template_requires_name(self) -> None:
        """Testa template sem nome."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="template",
        )
        with pytest.raises(ValidationError, match="template_name is required"):
            validate_template_message(request)

    def test_template_name_too_long(self) -> None:
        """Testa template com nome muito longo."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="template",
            template_name="x" * (MAX_TEMPLATE_NAME_LENGTH + 1),
        )
        with pytest.raises(ValidationError, match="template_name must not exceed"):
            validate_template_message(request)

    def test_template_valid(self) -> None:
        """Testa template válido."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="template",
            template_name="hello_world",
        )
        validate_template_message(request)

    def test_location_requires_lat_lon(self) -> None:
        """Testa location sem coordenadas."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="location",
        )
        with pytest.raises(ValidationError, match="latitude and location_longitude are required"):
            validate_location_message(request)

    def test_location_invalid_latitude(self) -> None:
        """Testa latitude inválida."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="location",
            location_latitude=91.0,  # Inválido
            location_longitude=0.0,
        )
        with pytest.raises(ValidationError, match="latitude must be between"):
            validate_location_message(request)

    def test_location_invalid_longitude(self) -> None:
        """Testa longitude inválida."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="location",
            location_latitude=0.0,
            location_longitude=181.0,  # Inválido
        )
        with pytest.raises(ValidationError, match="longitude must be between"):
            validate_location_message(request)

    def test_location_valid(self) -> None:
        """Testa location válida."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="location",
            location_latitude=-23.5505,
            location_longitude=-46.6333,
        )
        validate_location_message(request)

    def test_address_requires_at_least_one_field(self) -> None:
        """Testa address sem campos."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="address",
        )
        with pytest.raises(ValidationError, match="At least one address field"):
            validate_address_message(request)

    def test_address_valid(self) -> None:
        """Testa address válido."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="address",
            address_city="São Paulo",
        )
        validate_address_message(request)

    def test_contacts_placeholder(self) -> None:
        """Testa contacts (placeholder)."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="contacts",
        )
        # Não deve lançar (placeholder)
        validate_contacts_message(request)

    def test_reaction_placeholder(self) -> None:
        """Testa reaction (placeholder)."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="reaction",
        )
        # Não deve lançar (placeholder)
        validate_reaction_message(request)


class TestWhatsAppMessageValidatorOrchestrator:
    """Testa o orquestrador de validação."""

    def test_orchestrator_reexport(self) -> None:
        """Verifica reexport do orquestrador."""
        assert WhatsAppMessageValidator is ReexportedValidator

    def test_validate_outbound_complete_text(self) -> None:
        """Testa validação completa de texto."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="text",
            text="Olá!",
        )
        WhatsAppMessageValidator.validate_outbound_request(request)

    def test_validate_recipient_missing(self) -> None:
        """Testa destinatário ausente."""
        request = OutboundMessageRequest(
            to="",
            message_type="text",
            text="Olá!",
        )
        with pytest.raises(ValidationError, match="E.164 format"):
            WhatsAppMessageValidator.validate_outbound_request(request)

    def test_validate_recipient_invalid_format(self) -> None:
        """Testa formato de destinatário inválido."""
        request = OutboundMessageRequest(
            to="5511999999999",  # Falta +
            message_type="text",
            text="Olá!",
        )
        with pytest.raises(ValidationError, match="E.164 format"):
            WhatsAppMessageValidator.validate_outbound_request(request)

    def test_validate_message_type_missing(self) -> None:
        """Testa tipo de mensagem ausente."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="",
            text="Olá!",
        )
        with pytest.raises(ValidationError, match="message_type is required"):
            WhatsAppMessageValidator.validate_outbound_request(request)

    def test_validate_message_type_invalid(self) -> None:
        """Testa tipo de mensagem inválido."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="invalid",
            text="Olá!",
        )
        with pytest.raises(ValidationError, match="Invalid message_type"):
            WhatsAppMessageValidator.validate_outbound_request(request)

    def test_validate_category_valid(self) -> None:
        """Testa categoria válida."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="text",
            text="Olá!",
            category="MARKETING",
        )
        WhatsAppMessageValidator.validate_outbound_request(request)

    def test_validate_category_invalid(self) -> None:
        """Testa categoria inválida."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="text",
            text="Olá!",
            category="INVALID",
        )
        with pytest.raises(ValidationError, match="Invalid category"):
            WhatsAppMessageValidator.validate_outbound_request(request)

    def test_validate_idempotency_key_too_long(self) -> None:
        """Testa chave de idempotência muito longa."""
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="text",
            text="Olá!",
            idempotency_key="x" * (MAX_IDEMPOTENCY_KEY_LENGTH + 1),
        )
        with pytest.raises(ValidationError, match="idempotency_key must not exceed"):
            WhatsAppMessageValidator.validate_outbound_request(request)

    def test_validate_all_media_types(self) -> None:
        """Testa validação de todos os tipos de mídia."""
        for msg_type in ["image", "video", "audio", "document", "sticker"]:
            request = OutboundMessageRequest(
                to="+5511999999999",
                message_type=msg_type,
                media_id="123456",
            )
            WhatsAppMessageValidator.validate_outbound_request(request)

    def test_validate_interactive_types(self) -> None:
        """Testa validação de tipos interativos."""
        # Button
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="interactive",
            interactive_type="button",
            text="Escolha",
            buttons=[{"id": "1", "title": "A"}],
        )
        WhatsAppMessageValidator.validate_outbound_request(request)

        # List
        request = OutboundMessageRequest(
            to="+5511999999999",
            message_type="interactive",
            interactive_type="list",
            text="Escolha",
            buttons=[{"section": "items"}],
        )
        WhatsAppMessageValidator.validate_outbound_request(request)
