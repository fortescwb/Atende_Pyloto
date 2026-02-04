"""Contratos de entrada/saída para detecção de eventos.

Define dataclasses para o ponto de LLM #1: Event Detection.
Conforme REGRAS_E_PADROES.md § 2.1: ai/models contém DTOs para IA.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EventDetectionRequest:
    """Input para LLM #1 — Event Detector.

    Atributos:
        user_input: Mensagem recebida do usuário
        session_history: Histórico de mensagens (últimas N, já sanitizadas)
        known_intent: Intenção já detectada anteriormente (se houver)
        current_state: Estado atual da sessão (se houver)
    """

    user_input: str
    session_history: list[str] = field(default_factory=list)
    known_intent: str | None = None
    current_state: str | None = None


@dataclass(frozen=True, slots=True)
class EventDetectionResult:
    """Output de LLM #1 — resultado da classificação de evento.

    Atributos:
        event: Evento disparador classificado (ex: "USER_SENT_TEXT")
        detected_intent: Intenção detectada (ex: "GREETING", "SUPPORT_REQUEST")
        confidence: Confiança do classificador (0.0 a 1.0)
        requires_followup: True se requer validação adicional
        rationale: Justificativa da classificação (para debug)
    """

    event: str
    detected_intent: str
    confidence: float
    requires_followup: bool = False
    rationale: str | None = None

    def __post_init__(self) -> None:
        """Valida invariantes."""
        if not 0.0 <= self.confidence <= 1.0:
            object.__setattr__(
                self, "confidence", max(0.0, min(1.0, self.confidence))
            )
