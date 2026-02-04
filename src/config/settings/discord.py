"""Settings específicas de Discord.

Configurações do canal Discord via Discord API.

TODO: Implementar quando canal Discord for desenvolvido.
Referência: WhatsApp settings em config/settings/whatsapp.py
"""

from __future__ import annotations

# from dataclasses import dataclass
# from functools import lru_cache
# import os

# Constantes da Discord API
# DISCORD_API_VERSION: str = "v10"
# DISCORD_API_BASE_URL: str = "https://discord.com/api"


# @dataclass(frozen=True)
# class DiscordSettings:
#     """Configurações do canal Discord.
#
#     Attributes:
#         bot_token: Token do bot Discord
#         application_id: ID da aplicação Discord
#         public_key: Chave pública para verificação de interações
#         guild_id: ID do servidor (opcional, para bot específico de servidor)
#         api_version: Versão da API
#         api_base_url: URL base da API
#         request_timeout_seconds: Timeout para requisições HTTP
#         max_retries: Máximo de tentativas em caso de erro
#     """
#
#     # Credenciais
#     bot_token: str = ""
#     application_id: str = ""
#     public_key: str = ""
#     guild_id: str = ""
#
#     # API
#     api_version: str = DISCORD_API_VERSION
#     api_base_url: str = DISCORD_API_BASE_URL
#
#     # Timeouts e retries
#     request_timeout_seconds: float = 30.0
#     max_retries: int = 3
#
#     @property
#     def api_endpoint(self) -> str:
#         """URL base completa da API com versão."""
#         return f"{self.api_base_url}/{self.api_version}"
#
#     def validate(self) -> list[str]:
#         """Valida configurações mínimas de Discord."""
#         errors: list[str] = []
#         if not self.bot_token:
#             errors.append("DISCORD_BOT_TOKEN não configurado")
#         if not self.application_id:
#             errors.append("DISCORD_APPLICATION_ID não configurado")
#         return errors


# def _load_from_env() -> DiscordSettings:
#     """Carrega DiscordSettings de variáveis de ambiente."""
#     return DiscordSettings(
#         bot_token=os.getenv("DISCORD_BOT_TOKEN", ""),
#         application_id=os.getenv("DISCORD_APPLICATION_ID", ""),
#         public_key=os.getenv("DISCORD_PUBLIC_KEY", ""),
#         guild_id=os.getenv("DISCORD_GUILD_ID", ""),
#         api_version=os.getenv("DISCORD_API_VERSION", DISCORD_API_VERSION),
#         api_base_url=os.getenv("DISCORD_API_BASE_URL", DISCORD_API_BASE_URL),
#         request_timeout_seconds=float(
#             os.getenv("DISCORD_REQUEST_TIMEOUT_SECONDS", "30")
#         ),
#         max_retries=int(os.getenv("DISCORD_MAX_RETRIES", "3")),
#     )


# @lru_cache(maxsize=1)
# def get_discord_settings() -> DiscordSettings:
#     """Retorna instância cacheada de DiscordSettings."""
#     return _load_from_env()
