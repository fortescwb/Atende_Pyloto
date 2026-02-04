"""Settings específicas de Twitter/X.

Configurações do canal Twitter via Twitter API v2.

TODO: Implementar quando canal Twitter for desenvolvido.
Referência: WhatsApp settings em config/settings/whatsapp.py
"""

from __future__ import annotations

# from dataclasses import dataclass
# from functools import lru_cache
# import os

# Constantes da Twitter API
# TWITTER_API_VERSION: str = "2"
# TWITTER_API_BASE_URL: str = "https://api.twitter.com"


# @dataclass(frozen=True)
# class TwitterSettings:
#     """Configurações do canal Twitter/X.
#
#     Attributes:
#         bearer_token: Bearer Token para autenticação
#         api_key: API Key (Consumer Key)
#         api_secret: API Secret (Consumer Secret)
#         access_token: Access Token do usuário
#         access_token_secret: Access Token Secret do usuário
#         api_version: Versão da API
#         api_base_url: URL base da API
#         request_timeout_seconds: Timeout para requisições HTTP
#         max_retries: Máximo de tentativas em caso de erro
#     """
#
#     # Credenciais
#     bearer_token: str = ""
#     api_key: str = ""
#     api_secret: str = ""
#     access_token: str = ""
#     access_token_secret: str = ""
#
#     # API
#     api_version: str = TWITTER_API_VERSION
#     api_base_url: str = TWITTER_API_BASE_URL
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
#         """Valida configurações mínimas de Twitter."""
#         errors: list[str] = []
#         # Bearer token ou OAuth 1.0a é necessário
#         if not self.bearer_token and not (self.api_key and self.access_token):
#             errors.append(
#                 "TWITTER_BEARER_TOKEN ou TWITTER_API_KEY+ACCESS_TOKEN não configurado"
#             )
#         return errors


# def _load_from_env() -> TwitterSettings:
#     """Carrega TwitterSettings de variáveis de ambiente."""
#     return TwitterSettings(
#         bearer_token=os.getenv("TWITTER_BEARER_TOKEN", ""),
#         api_key=os.getenv("TWITTER_API_KEY", ""),
#         api_secret=os.getenv("TWITTER_API_SECRET", ""),
#         access_token=os.getenv("TWITTER_ACCESS_TOKEN", ""),
#         access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET", ""),
#         api_version=os.getenv("TWITTER_API_VERSION", TWITTER_API_VERSION),
#         api_base_url=os.getenv("TWITTER_API_BASE_URL", TWITTER_API_BASE_URL),
#         request_timeout_seconds=float(
#             os.getenv("TWITTER_REQUEST_TIMEOUT_SECONDS", "30")
#         ),
#         max_retries=int(os.getenv("TWITTER_MAX_RETRIES", "3")),
#     )


# @lru_cache(maxsize=1)
# def get_twitter_settings() -> TwitterSettings:
#     """Retorna instância cacheada de TwitterSettings."""
#     return _load_from_env()
