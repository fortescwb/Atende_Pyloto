"""Validadores de conformidade para mensagens WhatsApp/Meta.

Este pacote contém validadores especializados por tipo de mensagem,
separando responsabilidades conforme regras_e_padroes.md.

Uso:
    from api.validators.whatsapp import (
        WhatsAppMessageValidator,
        ValidationError,
    )

    validator = WhatsAppMessageValidator()
    validator.validate_outbound_request(request)
"""

from api.validators.whatsapp.errors import ValidationError
from api.validators.whatsapp.limits import (
    MAX_BUTTON_TEXT_LENGTH,
    MAX_BUTTONS_PER_MESSAGE,
    MAX_CAPTION_LENGTH,
    MAX_TEXT_LENGTH,
)
from api.validators.whatsapp.validator_dispatcher import WhatsAppMessageValidator

# Adiciona constantes como atributos de classe para compatibilidade
WhatsAppMessageValidator.MAX_TEXT_LENGTH = MAX_TEXT_LENGTH
WhatsAppMessageValidator.MAX_CAPTION_LENGTH = MAX_CAPTION_LENGTH
WhatsAppMessageValidator.MAX_BUTTONS_PER_MESSAGE = MAX_BUTTONS_PER_MESSAGE
WhatsAppMessageValidator.MAX_BUTTON_TEXT_LENGTH = MAX_BUTTON_TEXT_LENGTH

__all__ = [
    "MAX_BUTTONS_PER_MESSAGE",
    "MAX_BUTTON_TEXT_LENGTH",
    "MAX_CAPTION_LENGTH",
    "MAX_TEXT_LENGTH",
    "ValidationError",
    "WhatsAppMessageValidator",
]
