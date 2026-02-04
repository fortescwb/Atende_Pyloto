"""Settings específicas de Telegram.

Configurações do canal Telegram via Bot API.

TODO: Implementar quando canal Telegram for desenvolvido.
Referência: WhatsApp settings em config/settings/whatsapp.py
"""

from __future__ import annotations

# from dataclasses import dataclass
# from functools import lru_cache
# import os

# Constantes da Telegram Bot API
# TELEGRAM_API_BASE_URL: str = "https://api.telegram.org"


# @dataclass(frozen=True)
# class TelegramSettings:
#     """Configurações do canal Telegram.
#
#     Attributes:
#         bot_token: Token do bot Telegram (obtido via @BotFather)
#         webhook_secret: Secret para validação de webhooks
#         api_base_url: URL base da API
#         request_timeout_seconds: Timeout para requisições HTTP
#         max_retries: Máximo de tentativas em caso de erro
#     """
#
#     # Credenciais
#     bot_token: str = ""
#     webhook_secret: str = ""
#
#     # API
#     api_base_url: str = TELEGRAM_API_BASE_URL
#
#     # Timeouts e retries
#     request_timeout_seconds: float = 30.0
#     max_retries: int = 3
#
#     @property
#     def api_endpoint(self) -> str:
#         """URL base completa da API com token do bot."""
#         if not self.bot_token:
#             raise ValueError("bot_token é obrigatório")
#         return f"{self.api_base_url}/bot{self.bot_token}"
#
#     def validate(self) -> list[str]:
#         """Valida configurações mínimas de Telegram."""
#         errors: list[str] = []
#         if not self.bot_token:
#             errors.append("TELEGRAM_BOT_TOKEN não configurado")
#         return errors


# def _load_from_env() -> TelegramSettings:
#     """Carrega TelegramSettings de variáveis de ambiente."""
#     return TelegramSettings(
#         bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
#         webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET", ""),
#         api_base_url=os.getenv("TELEGRAM_API_BASE_URL", TELEGRAM_API_BASE_URL),
#         request_timeout_seconds=float(
#             os.getenv("TELEGRAM_REQUEST_TIMEOUT_SECONDS", "30")
#         ),
#         max_retries=int(os.getenv("TELEGRAM_MAX_RETRIES", "3")),
#     )


# @lru_cache(maxsize=1)
# def get_telegram_settings() -> TelegramSettings:
#     """Retorna instância cacheada de TelegramSettings."""
#     return _load_from_env()
