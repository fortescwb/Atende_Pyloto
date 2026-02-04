"""Core do módulo AI.

Exporta protocols e clients para uso externo.
A implementação OpenAIClient está em app/infra/ai/ (IO).
"""

from ai.core.client import AIClientProtocol
from ai.core.mock_client import MockAIClient

__all__ = [
    "AIClientProtocol",
    "MockAIClient",
]
