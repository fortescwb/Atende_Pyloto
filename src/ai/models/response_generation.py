"""Contratos de entrada/saída para geração de resposta.

Define dataclasses para o ponto de LLM #2: Response Generation.
Conforme REGRAS_E_PADROES.md § 2.1: ai/models contém DTOs para IA.
Conforme README.md: ResponseAgent gera 3 candidatos (formal, casual, empático).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResponseTone(Enum):
    """Tons de resposta disponíveis para candidatos."""

    FORMAL = "formal"  # Linguagem profissional e distante
    CASUAL = "casual"  # Linguagem amigável e descontraída
    EMPATHETIC = "empathetic"  # Linguagem acolhedora e compreensiva


@dataclass(frozen=True, slots=True)
class ResponseCandidate:
    """Um candidato de resposta com tom específico.

    Atributos:
        text_content: Conteúdo da resposta (1-4096 chars)
        tone: Tom da resposta (formal, casual, empathetic)
        confidence: Confiança neste candidato (0.0-1.0)
        rationale: Justificativa da geração (para debug)
    """

    text_content: str
    tone: ResponseTone
    confidence: float
    rationale: str | None = None

    def __post_init__(self) -> None:
        """Valida invariantes."""
        if not 0.0 <= self.confidence <= 1.0:
            object.__setattr__(
                self, "confidence", max(0.0, min(1.0, self.confidence))
            )
        if len(self.text_content) > 4096:
            object.__setattr__(
                self, "text_content", self.text_content[:4093] + "..."
            )


@dataclass(frozen=True, slots=True)
class ResponseOption:
    """Uma opção de resposta (para listas/botões).

    Atributos:
        id: ID único da opção (max 100 chars)
        title: Título exibido (max 512 chars)
        description: Descrição adicional opcional (max 1024 chars)
    """

    id: str
    title: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class ResponseGenerationRequest:
    """Input para LLM #2 — Response Generator.

    Atributos:
        event: Evento detectado (do LLM #1)
        detected_intent: Intenção do usuário
        current_state: Estado atual da sessão
        next_state: Próximo estado proposto (saída do FSM)
        user_input: Mensagem original do usuário
        session_context: Contexto adicional (lead profile, histórico)
        confidence_event: Confiança do evento (do LLM #1)
    """

    event: str
    detected_intent: str
    current_state: str
    next_state: str
    user_input: str
    session_context: dict[str, Any] = field(default_factory=dict)
    confidence_event: float = 0.5


@dataclass(frozen=True, slots=True)
class ResponseGenerationResult:
    """Output de LLM #2 — resposta gerada com múltiplos candidatos.

    Suporta tanto o modelo legado (text_content único) quanto o novo modelo
    com 3 candidatos (formal, casual, empático).

    Atributos:
        candidates: Tupla de candidatos de resposta (3: formal, casual, empático)
        text_content: Conteúdo principal da resposta (backwards compat)
        options: Opções para escolhas (se aplicável)
        suggested_next_state: Próximo estado sugerido pelo LLM
        requires_human_review: True se resposta requer revisão
        confidence: Confiança da resposta gerada (0.0-1.0)
        rationale: Justificativa da resposta (para debug)
    """

    candidates: tuple[ResponseCandidate, ...] = ()
    text_content: str = ""
    options: tuple[ResponseOption, ...] = ()
    suggested_next_state: str | None = None
    requires_human_review: bool = False
    confidence: float = 0.8
    rationale: str | None = None

    def __post_init__(self) -> None:
        """Valida invariantes e garante backwards compatibility."""
        if not 0.0 <= self.confidence <= 1.0:
            object.__setattr__(
                self, "confidence", max(0.0, min(1.0, self.confidence))
            )
        # Se há candidatos mas não text_content, usa o primeiro candidato
        if self.candidates and not self.text_content:
            object.__setattr__(
                self, "text_content", self.candidates[0].text_content
            )
        # Truncar texto se muito longo
        if len(self.text_content) > 4096:
            object.__setattr__(
                self, "text_content", self.text_content[:4093] + "..."
            )
