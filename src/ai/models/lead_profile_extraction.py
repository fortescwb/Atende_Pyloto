"""Models para LeadProfileAgent (Agente 2-B).

Request e Result para extração de dados do usuário.
Usa gpt-5-nano para extração rápida de informações.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class LeadProfileExtractionRequest:
    """Request para extração de dados do perfil do lead.

    Attributes:
        user_input: Mensagem do usuário
        current_profile_summary: Resumo do perfil atual (para context)
        current_personal_info: Texto de informações pessoais atual
        current_needs_summary: Resumo das necessidades ativas
    """

    user_input: str
    current_profile_summary: str = ""
    current_personal_info: str = ""
    current_needs_summary: str = ""


@dataclass(slots=True)
class LeadProfileExtractionResult:
    """Resultado da extração de dados do perfil.

    Attributes:
        personal_data: Dados pessoais extraídos (name, surname, email, company, city, state)
        personal_info_update: Texto atualizado para personal_info (ou None se sem mudança)
        need: Nova necessidade identificada (ou None se nenhuma)
        confidence: Confiança na extração (0.0-1.0)
        raw_response: Resposta bruta do LLM para debug
    """

    personal_data: dict[str, str] = field(default_factory=dict)
    personal_info_update: str | None = None
    need: dict[str, str] | None = None
    confidence: float = 0.0
    raw_response: str = ""

    @property
    def has_updates(self) -> bool:
        """Retorna True se há alguma atualização para aplicar."""
        return bool(self.personal_data) or self.personal_info_update is not None or self.need is not None

    def to_dict(self) -> dict[str, Any]:
        """Serializa para dicionário."""
        return {
            "personal_data": self.personal_data,
            "personal_info_update": self.personal_info_update,
            "need": self.need,
            "confidence": self.confidence,
        }
