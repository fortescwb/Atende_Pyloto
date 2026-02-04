"""Protocolos de domínio para stores de dedupe.

Interfaces leves (ABCs) dependidas por Application.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class DedupeProtocol(ABC):
    """Contrato mínimo síncrono para stores de deduplicação.

    Método canônico:
    - seen(key: str, ttl: int) -> bool
      Retorna True se a chave já foi vista (duplicado). Se não vista, marca-a
      com TTL e retorna False.
    """

    @abstractmethod
    def seen(self, key: str, ttl: int) -> bool:
        """Verifica e marca a chave de forma atômica.

        Args:
            key: Chave única (ex.: message_id ou hash)
            ttl: TTL em segundos

        Returns:
            True se já foi vista (duplicado); False se foi marcada agora (novo).
        """


class AsyncDedupeProtocol(ABC):
    """Contrato mínimo assíncrono para stores de deduplicação.

    Método canônico:
    - is_duplicate(key: str, ttl: int) -> bool
      Retorna True se a chave já foi vista (duplicado).
    - mark_processed(key: str, ttl: int) -> None
      Marca a chave como processada com TTL.
    """

    @abstractmethod
    async def is_duplicate(self, key: str, ttl: int = 3600) -> bool:
        """Verifica se a chave já foi processada.

        Args:
            key: Chave única (ex.: message_id)
            ttl: TTL padrão em segundos

        Returns:
            True se já foi vista (duplicado); False caso contrário.
        """

    @abstractmethod
    async def mark_processed(self, key: str, ttl: int = 3600) -> None:
        """Marca a chave como processada.

        Args:
            key: Chave única (ex.: message_id)
            ttl: TTL em segundos
        """
