"""Settings específicas de TikTok.

Configurações do canal TikTok via TikTok API.

TODO: Implementar quando canal TikTok for desenvolvido.
Referência: WhatsApp settings em config/settings/whatsapp.py
"""

from __future__ import annotations

# from dataclasses import dataclass
# from functools import lru_cache
# import os

# Constantes da TikTok API
# TIKTOK_API_BASE_URL: str = "https://open.tiktokapis.com"
# TIKTOK_API_VERSION: str = "v2"


# @dataclass(frozen=True)
# class TikTokSettings:
#     """Configurações do canal TikTok.
#
#     Attributes:
#         access_token: Token de acesso OAuth 2.0
#         client_key: Client Key do app TikTok
#         client_secret: Client Secret do app TikTok
#         api_version: Versão da API
#         api_base_url: URL base da API
#         request_timeout_seconds: Timeout para requisições HTTP
#         max_retries: Máximo de tentativas em caso de erro
#     """
#
#     # Credenciais OAuth
#     access_token: str = ""
#     client_key: str = ""
#     client_secret: str = ""
#
#     # API
#     api_version: str = TIKTOK_API_VERSION
#     api_base_url: str = TIKTOK_API_BASE_URL
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
#         """Valida configurações mínimas de TikTok."""
#         errors: list[str] = []
#         if not self.access_token:
#             errors.append("TIKTOK_ACCESS_TOKEN não configurado")
#         if not self.client_key:
#             errors.append("TIKTOK_CLIENT_KEY não configurado")
#         return errors


# def _load_from_env() -> TikTokSettings:
#     """Carrega TikTokSettings de variáveis de ambiente."""
#     return TikTokSettings(
#         access_token=os.getenv("TIKTOK_ACCESS_TOKEN", ""),
#         client_key=os.getenv("TIKTOK_CLIENT_KEY", ""),
#         client_secret=os.getenv("TIKTOK_CLIENT_SECRET", ""),
#         api_version=os.getenv("TIKTOK_API_VERSION", TIKTOK_API_VERSION),
#         api_base_url=os.getenv("TIKTOK_API_BASE_URL", TIKTOK_API_BASE_URL),
#         request_timeout_seconds=float(
#             os.getenv("TIKTOK_REQUEST_TIMEOUT_SECONDS", "30")
#         ),
#         max_retries=int(os.getenv("TIKTOK_MAX_RETRIES", "3")),
#     )


# @lru_cache(maxsize=1)
# def get_tiktok_settings() -> TikTokSettings:
#     """Retorna instância cacheada de TikTokSettings."""
#     return _load_from_env()
