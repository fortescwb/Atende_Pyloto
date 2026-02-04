"""Settings específicas de YouTube.

Configurações do canal YouTube via YouTube Data API.

TODO: Implementar quando canal YouTube for desenvolvido.
Referência: WhatsApp settings em config/settings/whatsapp.py
"""

from __future__ import annotations

# from dataclasses import dataclass
# from functools import lru_cache
# import os

# Constantes da YouTube API
# YOUTUBE_API_VERSION: str = "v3"
# YOUTUBE_API_BASE_URL: str = "https://www.googleapis.com/youtube"


# @dataclass(frozen=True)
# class YouTubeSettings:
#     """Configurações do canal YouTube.
#
#     Attributes:
#         api_key: Chave da API (para operações públicas)
#         access_token: Token de acesso OAuth 2.0 (para operações autenticadas)
#         client_id: Client ID do app Google
#         client_secret: Client Secret do app Google
#         channel_id: ID do canal YouTube
#         api_version: Versão da API
#         api_base_url: URL base da API
#         request_timeout_seconds: Timeout para requisições HTTP
#         max_retries: Máximo de tentativas em caso de erro
#     """
#
#     # Credenciais
#     api_key: str = ""
#     access_token: str = ""
#     client_id: str = ""
#     client_secret: str = ""
#     channel_id: str = ""
#
#     # API
#     api_version: str = YOUTUBE_API_VERSION
#     api_base_url: str = YOUTUBE_API_BASE_URL
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
#         """Valida configurações mínimas de YouTube."""
#         errors: list[str] = []
#         # API key ou access_token é necessário
#         if not self.api_key and not self.access_token:
#             errors.append("YOUTUBE_API_KEY ou YOUTUBE_ACCESS_TOKEN não configurado")
#         return errors


# def _load_from_env() -> YouTubeSettings:
#     """Carrega YouTubeSettings de variáveis de ambiente."""
#     return YouTubeSettings(
#         api_key=os.getenv("YOUTUBE_API_KEY", ""),
#         access_token=os.getenv("YOUTUBE_ACCESS_TOKEN", ""),
#         client_id=os.getenv("YOUTUBE_CLIENT_ID", ""),
#         client_secret=os.getenv("YOUTUBE_CLIENT_SECRET", ""),
#         channel_id=os.getenv("YOUTUBE_CHANNEL_ID", ""),
#         api_version=os.getenv("YOUTUBE_API_VERSION", YOUTUBE_API_VERSION),
#         api_base_url=os.getenv("YOUTUBE_API_BASE_URL", YOUTUBE_API_BASE_URL),
#         request_timeout_seconds=float(
#             os.getenv("YOUTUBE_REQUEST_TIMEOUT_SECONDS", "30")
#         ),
#         max_retries=int(os.getenv("YOUTUBE_MAX_RETRIES", "3")),
#     )


# @lru_cache(maxsize=1)
# def get_youtube_settings() -> YouTubeSettings:
#     """Retorna instância cacheada de YouTubeSettings."""
#     return _load_from_env()
