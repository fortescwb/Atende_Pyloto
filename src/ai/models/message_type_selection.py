"""Contratos de entrada/saída para seleção de tipo de mensagem.

Define dataclasses para o ponto de LLM #3: Message Type Selection.
Conforme REGRAS_E_PADROES.md § 2.1: ai/models contém DTOs para IA.
Conforme README.md: tipos válidos são text, interactive_button, interactive_list,
template, e reaction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MessageType(Enum):
    """Tipos de mensagem suportados para WhatsApp.

    TEXT: Mensagem de texto simples
    INTERACTIVE_BUTTON: Mensagem com botões de ação (max 3 opções)
    INTERACTIVE_LIST: Mensagem com lista de opções (max 10 opções)
    TEMPLATE: Mensagem template pré-aprovada
    REACTION: Apenas reação ao usuário (sem resposta textual)
        - Usar quando nenhuma resposta textual é necessária
        - Ex: usuário disse "blz, obg", apenas reagir com emoji
    """

    TEXT = "text"
    INTERACTIVE_BUTTON = "interactive_button"
    INTERACTIVE_LIST = "interactive_list"
    TEMPLATE = "template"
    REACTION = "reaction"


# Tipos válidos como strings para validação
VALID_MESSAGE_TYPES: frozenset[str] = frozenset({
    "text",
    "interactive_button",
    "interactive_list",
    "template",
    "reaction",
})


@dataclass(frozen=True, slots=True)
class MessageTypeSelectionRequest:
    """Input para LLM #3 — Message Type Selector.

    Atributos:
        text_content: Conteúdo da resposta (do LLM #2)
        options: Opções disponíveis (se houver)
        intent_type: Tipo de intent detectado
        user_preference: Preferência do usuário (se houver)
        turn_count: Número de turnos nesta sessão
    """

    text_content: str
    options: list[dict[str, str]] = field(default_factory=list)
    intent_type: str | None = None
    user_preference: str | None = None
    turn_count: int = 0


@dataclass(frozen=True, slots=True)
class MessageTypeSelectionResult:
    """Output de LLM #3 — tipo de mensagem selecionado.

    Atributos:
        message_type: Tipo de mensagem (text, interactive_button, etc.)
            Tipos válidos: text, interactive_button, interactive_list,
            template, reaction.
        parameters: Parâmetros específicos do tipo de mensagem
        confidence: Confiança da seleção (0.0-1.0)
        rationale: Justificativa da escolha (para debug)
        fallback: True se usou fallback heurístico
    """

    message_type: str
    parameters: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.8
    rationale: str | None = None
    fallback: bool = False

    def __post_init__(self) -> None:
        """Valida invariantes e tipo de mensagem."""
        if not 0.0 <= self.confidence <= 1.0:
            object.__setattr__(
                self, "confidence", max(0.0, min(1.0, self.confidence))
            )
        # Valida tipo de mensagem
        if self.message_type not in VALID_MESSAGE_TYPES:
            object.__setattr__(self, "message_type", "text")
