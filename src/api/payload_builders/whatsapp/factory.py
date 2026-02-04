"""Factory para obter o builder correto por tipo de mensagem."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from api.payload_builders.whatsapp.base import (
    PayloadBuilder,
    build_base_payload,
)
from api.payload_builders.whatsapp.interactive import (
    InteractivePayloadBuilder,
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
)
from api.payload_builders.whatsapp.template import (
    TemplatePayloadBuilder,
)
from api.payload_builders.whatsapp.text import (
    TextPayloadBuilder,
)
from app.constants.whatsapp import MessageType

if TYPE_CHECKING:
    from api.connectors.whatsapp.models import OutboundMessageRequest

# Mapeamento de tipo de mensagem para builder
_BUILDERS: dict[MessageType, PayloadBuilder] = {
    MessageType.TEXT: TextPayloadBuilder(),
    MessageType.IMAGE: ImagePayloadBuilder(),
    MessageType.VIDEO: VideoPayloadBuilder(),
    MessageType.AUDIO: AudioPayloadBuilder(),
    MessageType.DOCUMENT: DocumentPayloadBuilder(),
    MessageType.LOCATION: LocationPayloadBuilder(),
    MessageType.ADDRESS: AddressPayloadBuilder(),
    MessageType.INTERACTIVE: InteractivePayloadBuilder(),
}

_TEMPLATE_BUILDER = TemplatePayloadBuilder()


def get_payload_builder(message_type: MessageType) -> PayloadBuilder | None:
    """Retorna o builder para o tipo de mensagem.

    Args:
        message_type: Tipo de mensagem

    Returns:
        Builder apropriado ou None se não suportado
    """
    return _BUILDERS.get(message_type)


def build_full_payload(request: OutboundMessageRequest) -> dict[str, Any]:
    """Constrói payload completo para a API Meta.

    Args:
        request: Requisição de envio

    Returns:
        Payload completo pronto para envio

    Raises:
        ValueError: Se tipo de mensagem não suportado
    """
    payload = build_base_payload(request)

    # Template tem prioridade sobre tipo de mensagem
    if request.template_name:
        payload.update(_TEMPLATE_BUILDER.build(request))
        return payload

    # Obtém builder pelo tipo
    msg_type = MessageType(request.message_type)
    builder = get_payload_builder(msg_type)

    if builder is None:
        raise ValueError(f"Tipo de mensagem não suportado: {msg_type}")

    payload.update(builder.build(request))
    return payload
