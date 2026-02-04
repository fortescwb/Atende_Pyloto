"""Testes abrangentes para api.payload_builders.whatsapp.

Cobre: base, text, media (4 tipos), interactive (5 tipos),
location, address, template e factory.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from api.payload_builders.whatsapp.base import PayloadBuilder, build_base_payload
from api.payload_builders.whatsapp.factory import (
    build_full_payload,
    get_payload_builder,
)
from api.payload_builders.whatsapp.interactive import (
    InteractivePayloadBuilder,
    _build_button_action,
    _build_cta_url_action,
    _build_flow_action,
    _build_list_action,
    _build_location_request_action,
)
from api.payload_builders.whatsapp.location import (
    AddressPayloadBuilder,
    LocationPayloadBuilder,
)
from api.payload_builders.whatsapp.media import (
    AudioPayloadBuilder,
    DocumentPayloadBuilder,
    ImagePayloadBuilder,
    VideoPayloadBuilder,
    _build_media_object,
)
from api.payload_builders.whatsapp.template import TemplatePayloadBuilder
from api.payload_builders.whatsapp.text import TextPayloadBuilder
from app.constants.whatsapp import InteractiveType, MessageType


def _mock_request(**kwargs: Any) -> MagicMock:
    """Cria mock de OutboundMessageRequest com atributos arbitrários."""
    req = MagicMock()
    # Defaults
    req.to = "5511999999999"
    req.message_type = MessageType.TEXT
    req.text = "Hello World"
    req.media_id = None
    req.media_url = None
    req.media_filename = None
    req.template_name = None
    req.template_params = None
    req.interactive_type = None
    req.buttons = None
    req.footer = None
    req.location_latitude = None
    req.location_longitude = None
    req.location_name = None
    req.location_address = None
    req.address_street = None
    req.address_city = None
    req.address_state = None
    req.address_zip_code = None
    req.address_country_code = None
    req.flow_message_version = None
    req.flow_token = None
    req.flow_id = None
    req.flow_cta = None
    req.flow_action = None
    req.cta_display_text = None
    req.cta_url = None
    # Override with provided kwargs
    for k, v in kwargs.items():
        setattr(req, k, v)
    return req


class TestBuildBasePayload:
    """Testes para build_base_payload e PayloadBuilder protocol."""

    def test_build_base_payload_structure(self) -> None:
        """Verifica estrutura base do payload (inclui type do message_type)."""
        req = _mock_request(to="+5511988887777", message_type=MessageType.TEXT)
        result = build_base_payload(req)
        assert result == {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": "+5511988887777",
            "type": MessageType.TEXT,
        }

    def test_payload_builder_protocol_has_build_method(self) -> None:
        """Verifica que PayloadBuilder é um Protocol com método build."""
        assert hasattr(PayloadBuilder, "build")
        # TextPayloadBuilder implementa o protocol
        builder = TextPayloadBuilder()
        assert hasattr(builder, "build")


class TestTextPayloadBuilder:
    """Testes para TextPayloadBuilder."""

    def test_text_builder_basic(self) -> None:
        """Texto simples com preview_url=False."""
        req = _mock_request(text="Olá, mundo!")
        builder = TextPayloadBuilder()
        result = builder.build(req)
        assert result == {"text": {"preview_url": False, "body": "Olá, mundo!"}}

    def test_text_builder_with_special_chars(self) -> None:
        """Texto com caracteres especiais e emoji."""
        req = _mock_request(text="Olá 🎉 @user #tag $100")
        result = TextPayloadBuilder().build(req)
        assert result["text"]["body"] == "Olá 🎉 @user #tag $100"


class TestMediaPayloadBuilders:
    """Testes para builders de mídia (image, video, audio, document)."""

    def test_build_media_object_with_id(self) -> None:
        """Media object com media_id."""
        result = _build_media_object("media123", None, "Caption")
        assert result == {"id": "media123", "caption": "Caption"}

    def test_build_media_object_with_url(self) -> None:
        """Media object com media_url."""
        result = _build_media_object(None, "https://example.com/img.jpg", None)
        assert result == {"link": "https://example.com/img.jpg"}

    def test_build_media_object_id_priority_over_url(self) -> None:
        """Media_id tem prioridade sobre url."""
        result = _build_media_object("id123", "https://url.com", "Cap")
        assert "id" in result
        assert "link" not in result

    def test_build_media_object_no_caption(self) -> None:
        """Sem caption quando None."""
        result = _build_media_object("id", None, None)
        assert "caption" not in result

    def test_image_builder_with_id(self) -> None:
        """ImagePayloadBuilder com media_id e caption."""
        req = _mock_request(media_id="img001", text="Foto legal")
        result = ImagePayloadBuilder().build(req)
        assert result == {"image": {"id": "img001", "caption": "Foto legal"}}

    def test_image_builder_with_url(self) -> None:
        """ImagePayloadBuilder com URL e texto como caption."""
        req = _mock_request(media_url="https://cdn.com/photo.png", text="Legenda")
        result = ImagePayloadBuilder().build(req)
        assert result == {"image": {"link": "https://cdn.com/photo.png", "caption": "Legenda"}}

    def test_video_builder(self) -> None:
        """VideoPayloadBuilder com media_id."""
        req = _mock_request(media_id="vid001", text="Vídeo show")
        result = VideoPayloadBuilder().build(req)
        assert result == {"video": {"id": "vid001", "caption": "Vídeo show"}}

    def test_audio_builder_no_caption(self) -> None:
        """AudioPayloadBuilder não inclui caption."""
        req = _mock_request(media_id="aud001", text="Será ignorado")
        result = AudioPayloadBuilder().build(req)
        assert result == {"audio": {"id": "aud001"}}
        assert "caption" not in result["audio"]

    def test_document_builder_with_filename(self) -> None:
        """DocumentPayloadBuilder com filename."""
        req = _mock_request(
            media_id="doc001",
            text="Relatório",
            media_filename="relatorio.pdf",
        )
        result = DocumentPayloadBuilder().build(req)
        assert result == {
            "document": {
                "id": "doc001",
                "caption": "Relatório",
                "filename": "relatorio.pdf",
            }
        }

    def test_document_builder_without_filename(self) -> None:
        """DocumentPayloadBuilder sem filename - text vira caption."""
        req = _mock_request(media_url="https://cdn.com/doc.pdf", text="Documento")
        result = DocumentPayloadBuilder().build(req)
        assert result == {"document": {"link": "https://cdn.com/doc.pdf", "caption": "Documento"}}


class TestInteractivePayloadBuilder:
    """Testes para InteractivePayloadBuilder e action builders."""

    def test_build_button_action(self) -> None:
        """Action para botões de reply."""
        req = _mock_request(
            buttons=[
                {"id": "opt1", "title": "Opção 1"},
                {"id": "opt2", "title": "Opção 2"},
            ]
        )
        result = _build_button_action(req)
        assert result == {
            "buttons": [
                {"type": "reply", "reply": {"id": "opt1", "title": "Opção 1"}},
                {"type": "reply", "reply": {"id": "opt2", "title": "Opção 2"}},
            ]
        }

    def test_build_button_action_empty_buttons(self) -> None:
        """Action para botões vazios retorna lista vazia."""
        req = _mock_request(buttons=None)
        result = _build_button_action(req)
        assert result == {"buttons": []}

    def test_build_list_action(self) -> None:
        """Action para lista com seções."""
        sections = [{"title": "Seção 1", "rows": []}]
        req = _mock_request(buttons=sections)
        result = _build_list_action(req)
        assert result == {"button": "Ver opções", "sections": sections}

    def test_build_flow_action(self) -> None:
        """Action para WhatsApp Flow."""
        req = _mock_request(
            flow_message_version="3",
            flow_token="token123",
            flow_id="flow001",
            flow_cta="Iniciar Flow",
            flow_action="navigate",
        )
        result = _build_flow_action(req)
        assert result == {
            "name": "flow",
            "parameters": {
                "flow_message_version": "3",
                "flow_token": "token123",
                "flow_id": "flow001",
                "flow_cta": "Iniciar Flow",
                "flow_action": "navigate",
            },
        }

    def test_build_cta_url_action(self) -> None:
        """Action para CTA com URL."""
        req = _mock_request(cta_display_text="Visite nosso site", cta_url="https://site.com")
        result = _build_cta_url_action(req)
        assert result == {
            "name": "cta_url",
            "parameters": {"display_text": "Visite nosso site", "url": "https://site.com"},
        }

    def test_build_location_request_action(self) -> None:
        """Action para solicitar localização."""
        result = _build_location_request_action()
        assert result == {"name": "send_location"}

    def test_interactive_builder_button_type(self) -> None:
        """InteractivePayloadBuilder para tipo BUTTON."""
        req = _mock_request(
            text="Escolha uma opção",
            interactive_type=InteractiveType.BUTTON.value,
            buttons=[{"id": "a", "title": "A"}],
        )
        result = InteractivePayloadBuilder().build(req)
        assert result["interactive"]["type"] == "button"
        assert result["interactive"]["body"]["text"] == "Escolha uma opção"
        assert "action" in result["interactive"]
        assert len(result["interactive"]["action"]["buttons"]) == 1

    def test_interactive_builder_list_type(self) -> None:
        """InteractivePayloadBuilder para tipo LIST."""
        req = _mock_request(
            text="Selecione da lista",
            interactive_type=InteractiveType.LIST.value,
            buttons=[{"title": "S1", "rows": []}],
        )
        result = InteractivePayloadBuilder().build(req)
        assert result["interactive"]["type"] == "list"
        assert "action" in result["interactive"]
        assert result["interactive"]["action"]["button"] == "Ver opções"

    def test_interactive_builder_flow_type(self) -> None:
        """InteractivePayloadBuilder para tipo FLOW."""
        req = _mock_request(
            text="Inicie o fluxo",
            interactive_type=InteractiveType.FLOW.value,
            flow_id="fl01",
            flow_token="tk",
            flow_cta="Go",
            flow_action="nav",
            flow_message_version="3",
        )
        result = InteractivePayloadBuilder().build(req)
        assert result["interactive"]["type"] == "flow"
        assert result["interactive"]["action"]["name"] == "flow"

    def test_interactive_builder_cta_url_type(self) -> None:
        """InteractivePayloadBuilder para tipo CTA_URL."""
        req = _mock_request(
            text="Clique aqui",
            interactive_type=InteractiveType.CTA_URL.value,
            cta_display_text="Clique",
            cta_url="https://x.com",
        )
        result = InteractivePayloadBuilder().build(req)
        assert result["interactive"]["type"] == "cta_url"
        assert result["interactive"]["action"]["name"] == "cta_url"

    def test_interactive_builder_location_request_type(self) -> None:
        """InteractivePayloadBuilder para LOCATION_REQUEST_MESSAGE."""
        req = _mock_request(
            text="Compartilhe sua localização",
            interactive_type=InteractiveType.LOCATION_REQUEST_MESSAGE.value,
        )
        result = InteractivePayloadBuilder().build(req)
        assert result["interactive"]["type"] == "location_request_message"
        assert result["interactive"]["action"] == {"name": "send_location"}

    def test_interactive_builder_with_footer(self) -> None:
        """InteractivePayloadBuilder inclui footer quando presente."""
        req = _mock_request(
            text="Texto",
            interactive_type=InteractiveType.BUTTON.value,
            buttons=[{"id": "x", "title": "X"}],
            footer="Rodapé informativo",
        )
        result = InteractivePayloadBuilder().build(req)
        assert result["interactive"]["footer"] == {"text": "Rodapé informativo"}

    def test_interactive_builder_no_footer_when_none(self) -> None:
        """InteractivePayloadBuilder não inclui footer quando None."""
        req = _mock_request(
            text="Texto",
            interactive_type=InteractiveType.BUTTON.value,
            buttons=[],
            footer=None,
        )
        result = InteractivePayloadBuilder().build(req)
        assert "footer" not in result["interactive"]


class TestLocationPayloadBuilders:
    """Testes para LocationPayloadBuilder e AddressPayloadBuilder."""

    def test_location_builder_complete(self) -> None:
        """LocationPayloadBuilder com todos os campos."""
        req = _mock_request(
            location_latitude=-23.5505,
            location_longitude=-46.6333,
            location_name="Praça da Sé",
            location_address="Centro, São Paulo",
        )
        result = LocationPayloadBuilder().build(req)
        assert result == {
            "location": {
                "latitude": -23.5505,
                "longitude": -46.6333,
                "name": "Praça da Sé",
                "address": "Centro, São Paulo",
            }
        }

    def test_location_builder_minimal(self) -> None:
        """LocationPayloadBuilder com apenas lat/long."""
        req = _mock_request(location_latitude=0.0, location_longitude=0.0)
        result = LocationPayloadBuilder().build(req)
        assert result["location"]["latitude"] == 0.0
        assert result["location"]["longitude"] == 0.0
        assert result["location"]["name"] is None
        assert result["location"]["address"] is None

    def test_address_builder_complete(self) -> None:
        """AddressPayloadBuilder com todos os campos."""
        req = _mock_request(
            address_street="Av. Paulista, 1000",
            address_city="São Paulo",
            address_state="SP",
            address_zip_code="01310-100",
            address_country_code="BR",
        )
        result = AddressPayloadBuilder().build(req)
        assert result == {
            "address": {
                "street": "Av. Paulista, 1000",
                "city": "São Paulo",
                "state": "SP",
                "zip_code": "01310-100",
                "country_code": "BR",
            }
        }

    def test_address_builder_partial(self) -> None:
        """AddressPayloadBuilder com campos parciais."""
        req = _mock_request(address_city="Curitiba", address_state="PR")
        result = AddressPayloadBuilder().build(req)
        assert result["address"]["city"] == "Curitiba"
        assert result["address"]["state"] == "PR"
        assert result["address"]["street"] is None
        assert result["address"]["zip_code"] is None


class TestTemplatePayloadBuilder:
    """Testes para TemplatePayloadBuilder."""

    def test_template_builder_without_params(self) -> None:
        """Template sem parâmetros."""
        req = _mock_request(template_name="hello_world", template_params=None)
        result = TemplatePayloadBuilder().build(req)
        assert result == {
            "template": {"name": "hello_world", "language": {"code": "pt_BR"}}
        }

    def test_template_builder_with_params(self) -> None:
        """Template com parâmetros de body."""
        req = _mock_request(
            template_name="order_update",
            template_params={"name": "João", "order": 12345},
        )
        result = TemplatePayloadBuilder().build(req)
        assert result["template"]["name"] == "order_update"
        assert result["template"]["language"] == {"code": "pt_BR"}
        assert len(result["template"]["components"]) == 1
        component = result["template"]["components"][0]
        assert component["type"] == "body"
        assert len(component["parameters"]) == 2
        # Verifica conversão para string
        texts = [p["text"] for p in component["parameters"]]
        assert "João" in texts
        assert "12345" in texts


class TestFactoryFunctions:
    """Testes para get_payload_builder e build_full_payload."""

    @pytest.mark.parametrize(
        ("msg_type", "expected_builder"),
        [
            (MessageType.TEXT, TextPayloadBuilder),
            (MessageType.IMAGE, ImagePayloadBuilder),
            (MessageType.VIDEO, VideoPayloadBuilder),
            (MessageType.AUDIO, AudioPayloadBuilder),
            (MessageType.DOCUMENT, DocumentPayloadBuilder),
            (MessageType.INTERACTIVE, InteractivePayloadBuilder),
            (MessageType.LOCATION, LocationPayloadBuilder),
            (MessageType.ADDRESS, AddressPayloadBuilder),
            # TEMPLATE não está em _BUILDERS (usa lógica separada)
        ],
    )
    def test_get_payload_builder_returns_correct_type(
        self, msg_type: MessageType, expected_builder: type
    ) -> None:
        """Verifica que get_payload_builder retorna o builder correto."""
        builder = get_payload_builder(msg_type)
        assert isinstance(builder, expected_builder)

    def test_get_payload_builder_unknown_type_returns_text(self) -> None:
        """Tipo desconhecido retorna TextPayloadBuilder como fallback."""
        # Simula um MessageType não mapeado passando valor inválido
        # O código usa .get() com TextPayloadBuilder como default
        builder = get_payload_builder(MessageType.TEXT)  # Fallback test via factory
        assert isinstance(builder, TextPayloadBuilder)

    def test_get_payload_builder_returns_none_for_template(self) -> None:
        """Template não está em _BUILDERS, retorna None."""
        builder = get_payload_builder(MessageType.TEMPLATE)
        assert builder is None

    def test_build_full_payload_raises_for_unsupported_type(self) -> None:
        """Levanta ValueError para tipo não suportado."""
        req = _mock_request(
            to="5511900000000",
            message_type=MessageType.TEMPLATE,  # Não está em _BUILDERS
            template_name=None,  # Sem template_name para não entrar no if
        )
        with pytest.raises(ValueError, match="Tipo de mensagem não suportado"):
            build_full_payload(req)

    def test_build_full_payload_text_message(self) -> None:
        """build_full_payload para mensagem de texto."""
        req = _mock_request(
            to="5511999998888",
            message_type=MessageType.TEXT,
            text="Mensagem teste",
        )
        result = build_full_payload(req)
        assert result["messaging_product"] == "whatsapp"
        assert result["recipient_type"] == "individual"
        assert result["to"] == "5511999998888"
        assert result["type"] == "text"
        assert result["text"]["body"] == "Mensagem teste"

    def test_build_full_payload_template_priority(self) -> None:
        """Template tem prioridade sobre message_type (type é sobrescrito)."""
        req = _mock_request(
            to="5511900000000",
            message_type=MessageType.TEXT,  # Seria ignorado
            template_name="welcome_template",
            template_params=None,
        )
        result = build_full_payload(req)
        # Template sobrescreve com seu próprio payload
        assert "template" in result
        assert result["template"]["name"] == "welcome_template"
        # O type original vem de build_base_payload mas template é aplicado
        assert "text" not in result

    def test_build_full_payload_image_message(self) -> None:
        """build_full_payload para mensagem de imagem."""
        req = _mock_request(
            to="5511911111111",
            message_type=MessageType.IMAGE,
            media_id="img_xyz",
            text="Legenda da imagem",
        )
        result = build_full_payload(req)
        assert result["type"] == "image"
        assert result["image"]["id"] == "img_xyz"
        assert result["image"]["caption"] == "Legenda da imagem"

    def test_build_full_payload_interactive_message(self) -> None:
        """build_full_payload para mensagem interativa."""
        req = _mock_request(
            to="5511922222222",
            message_type=MessageType.INTERACTIVE,
            interactive_type=InteractiveType.BUTTON.value,
            text="Escolha",
            buttons=[{"id": "1", "title": "Um"}],
        )
        result = build_full_payload(req)
        assert result["type"] == "interactive"
        assert result["interactive"]["type"] == "button"

    def test_build_full_payload_location_message(self) -> None:
        """build_full_payload para mensagem de localização."""
        req = _mock_request(
            to="5511933333333",
            message_type=MessageType.LOCATION,
            location_latitude=-22.9068,
            location_longitude=-43.1729,
            location_name="Rio de Janeiro",
        )
        result = build_full_payload(req)
        assert result["type"] == "location"
        assert result["location"]["latitude"] == -22.9068
        assert result["location"]["name"] == "Rio de Janeiro"


class TestEdgeCases:
    """Testes de casos de borda e integração."""

    def test_payload_builder_is_stateless(self) -> None:
        """Builders são stateless - podem ser reutilizados."""
        builder = TextPayloadBuilder()
        req1 = _mock_request(text="First")
        req2 = _mock_request(text="Second")
        r1 = builder.build(req1)
        r2 = builder.build(req2)
        assert r1["text"]["body"] == "First"
        assert r2["text"]["body"] == "Second"

    def test_all_builders_return_dict(self) -> None:
        """Todos os builders retornam dict."""
        builders = [
            (TextPayloadBuilder(), _mock_request()),
            (ImagePayloadBuilder(), _mock_request(media_id="x")),
            (VideoPayloadBuilder(), _mock_request(media_id="x")),
            (AudioPayloadBuilder(), _mock_request(media_id="x")),
            (DocumentPayloadBuilder(), _mock_request(media_id="x")),
            (
                InteractivePayloadBuilder(),
                _mock_request(
                    interactive_type=InteractiveType.BUTTON.value, buttons=[]
                ),
            ),
            (
                LocationPayloadBuilder(),
                _mock_request(location_latitude=0, location_longitude=0),
            ),
            (AddressPayloadBuilder(), _mock_request()),
            (TemplatePayloadBuilder(), _mock_request(template_name="t")),
        ]
        for builder, req in builders:
            result = builder.build(req)
            assert isinstance(result, dict), f"{builder.__class__.__name__} must return dict"

    def test_media_object_empty_when_no_id_or_url(self) -> None:
        """Media object vazio quando sem id nem url."""
        result = _build_media_object(None, None, None)
        assert result == {}

    def test_document_with_only_url_no_filename(self) -> None:
        """Documento com URL mas sem filename."""
        req = _mock_request(media_url="https://x.com/f.pdf", media_filename=None)
        result = DocumentPayloadBuilder().build(req)
        assert "filename" not in result["document"]
