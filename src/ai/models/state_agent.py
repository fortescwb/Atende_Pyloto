"""Contratos de entrada/saída para o agente de estado.

Define dataclasses para o ponto de LLM #1: State Agent.
O StateAgent identifica o estado atual da conversa e sugere próximos estados válidos.

Conforme REGRAS_E_PADROES.md § 2.1: ai/models contém DTOs para IA.
Conforme README.md: StateAgent (LLM #1) - prev_state, curr_state, next_states.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SuggestedState:
    """Uma sugestão de próximo estado válido.

    Atributos:
        state: Nome do SessionState sugerido
        confidence: Confiança nesta sugestão (0.0-1.0)
        reasoning: Justificativa curta para esta sugestão
    """

    state: str
    confidence: float
    reasoning: str

    def __post_init__(self) -> None:
        """Valida invariantes."""
        if not 0.0 <= self.confidence <= 1.0:
            object.__setattr__(
                self, "confidence", max(0.0, min(1.0, self.confidence))
            )
        if not self.state:
            raise ValueError("state não pode ser vazio")


@dataclass(frozen=True, slots=True)
class StateAgentRequest:
    """Input para LLM #1 — State Agent.

    Atributos:
        user_input: Mensagem original do usuário
        current_state: Estado atual da sessão (SessionState.name)
        conversation_history: Resumo do histórico da conversa (sem PII)
        valid_transitions: Estados possíveis a partir do atual
    """

    user_input: str
    current_state: str
    conversation_history: str
    valid_transitions: tuple[str, ...]

    def __post_init__(self) -> None:
        """Valida invariantes."""
        if not self.user_input:
            raise ValueError("user_input não pode ser vazio")
        if not self.current_state:
            raise ValueError("current_state não pode ser vazio")


@dataclass(frozen=True, slots=True)
class StateAgentResult:
    """Output de LLM #1 — análise de estado da conversa.

    Atributos:
        previous_state: Estado anterior da sessão
        current_state: Estado identificado como atual
        suggested_next_states: Lista de próximos estados sugeridos (max 3)
        detected_intent: Intenção do usuário detectada (ex: 'agendar', 'dúvida', 'reclamação')
        confidence: Confiança geral na análise (0.0-1.0)
        rationale: Justificativa da análise (para debug/auditoria)
    """

    previous_state: str
    current_state: str
    suggested_next_states: tuple[SuggestedState, ...]
    detected_intent: str | None = None
    confidence: float = 0.5
    rationale: str | None = None

    def __post_init__(self) -> None:
        """Valida invariantes."""
        # Normaliza confiança para range válido
        if not 0.0 <= self.confidence <= 1.0:
            object.__setattr__(
                self, "confidence", max(0.0, min(1.0, self.confidence))
            )
        # Limita sugestões a máximo de 3
        if len(self.suggested_next_states) > 3:
            object.__setattr__(
                self, "suggested_next_states", self.suggested_next_states[:3]
            )
