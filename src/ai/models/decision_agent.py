"""Contratos de entrada/saída para o agente de decisão.

Define dataclasses para o ponto de LLM #4: Decision Agent.
O DecisionAgent consolida outputs dos 3 agentes anteriores e toma decisão final.

Conforme REGRAS_E_PADROES.md § 2.1: ai/models contém DTOs para IA.
Conforme README.md: DecisionAgent (LLM #4) - consolida, escolhe, aplica threshold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai.models.message_type_selection import MessageTypeSelectionResult
    from ai.models.response_generation import ResponseGenerationResult
    from ai.models.state_agent import StateAgentResult

# Threshold de confiança mínimo para aceitar decisão (conforme README.md)
CONFIDENCE_THRESHOLD: float = 0.7

# Número de falhas consecutivas para escalação (conforme README.md)
ESCALATION_CONSECUTIVE_FAILURES: int = 3

# Fallback de resposta quando confiança < threshold (conforme README.md)
FALLBACK_RESPONSE: str = "Desculpe, não entendi. Pode reformular?"


@dataclass(frozen=True, slots=True)
class DecisionAgentRequest:
    """Input para LLM #4 — Decision Agent.

    Atributos:
        state_result: Resultado do StateAgent (LLM #1)
        response_result: Resultado do ResponseAgent (LLM #2)
        message_type_result: Resultado do MessageTypeAgent (LLM #3)
        user_input: Mensagem original do usuário
        consecutive_low_confidence: Contador para escalação (0-3)
    """

    state_result: StateAgentResult
    response_result: ResponseGenerationResult
    message_type_result: MessageTypeSelectionResult
    user_input: str
    consecutive_low_confidence: int = 0

    def __post_init__(self) -> None:
        """Valida invariantes."""
        if not self.user_input:
            raise ValueError("user_input não pode ser vazio")
        if self.consecutive_low_confidence < 0:
            object.__setattr__(self, "consecutive_low_confidence", 0)


@dataclass(frozen=True, slots=True)
class DecisionAgentResult:
    """Output de LLM #4 — decisão final consolidada.

    Atributos:
        final_state: Estado final escolhido (SessionState.name)
        final_text: Texto final da resposta escolhida
        final_message_type: Tipo de mensagem escolhido
        understood: True se confidence >= threshold (0.7)
        confidence: Confiança final consolidada (0.0-1.0)
        should_escalate: True se deve escalar para humano
        rationale: Justificativa da decisão (para debug/auditoria)
    """

    final_state: str
    final_text: str
    final_message_type: str
    understood: bool
    confidence: float
    should_escalate: bool = False
    rationale: str | None = None

    def __post_init__(self) -> None:
        """Valida invariantes e deriva campos."""
        # Normaliza confiança para range válido
        if not 0.0 <= self.confidence <= 1.0:
            object.__setattr__(
                self, "confidence", max(0.0, min(1.0, self.confidence))
            )
        # Deriva understood a partir do threshold
        expected_understood = self.confidence >= CONFIDENCE_THRESHOLD
        if self.understood != expected_understood:
            object.__setattr__(self, "understood", expected_understood)
