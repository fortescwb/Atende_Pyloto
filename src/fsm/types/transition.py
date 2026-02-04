"""
Tipos e estruturas de dados para transições de estado.

Este módulo define os tipos usados para representar e rastrear
transições entre estados na FSM.

Referência: REGRAS_E_PADROES.md § 1.3 — Determinismo e previsibilidade
Referência: FUNCIONAMENTO.md § 8 — Observabilidade e auditoria
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from fsm.states.session import SessionState


@dataclass(frozen=True, slots=True)
class StateTransition:
    """
    Representa uma transição de estado na FSM.

    Registro imutável de uma mudança de estado, incluindo:
    - Estados de origem e destino
    - Gatilho que causou a transição
    - Metadados para auditoria (sem PII)
    - Timestamp da transição
    - Nível de confiança (útil para decisões via IA)

    Attributes:
        from_state: Estado de origem da transição
        to_state: Estado de destino da transição
        trigger: Identificador do gatilho que causou a transição
        metadata: Dados adicionais para auditoria (nunca conter PII)
        timestamp: Momento da transição (UTC)
        confidence: Nível de confiança na transição (0.0 a 1.0)
    """

    from_state: SessionState
    to_state: SessionState
    trigger: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    confidence: float = 1.0

    def __post_init__(self) -> None:
        """Valida invariantes do objeto após inicialização."""
        # Valida range de confidence
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence deve estar entre 0.0 e 1.0, recebido: {self.confidence}"
            )

        # Valida que trigger não é vazio
        if not self.trigger or not self.trigger.strip():
            raise ValueError("trigger não pode ser vazio")

    def to_log_dict(self) -> dict[str, Any]:
        """
        Retorna representação segura para logs (sem PII).

        Returns:
            Dict com dados seguros para logging estruturado
        """
        return {
            "from_state": self.from_state.name,
            "to_state": self.to_state.name,
            "trigger": self.trigger,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            # metadata é incluído pois deve ser livre de PII por contrato
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class TransitionResult:
    """
    Resultado de uma tentativa de transição.

    Attributes:
        success: Se a transição foi bem-sucedida
        transition: Dados da transição (se success=True)
        error_reason: Motivo da falha (se success=False)
    """

    success: bool
    transition: StateTransition | None = None
    error_reason: str | None = None

    def __post_init__(self) -> None:
        """Valida consistência do resultado."""
        if self.success and self.transition is None:
            raise ValueError("Transição bem-sucedida deve incluir transition")
        if not self.success and self.error_reason is None:
            raise ValueError("Transição falha deve incluir error_reason")
