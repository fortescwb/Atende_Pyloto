"""Settings específicas de Email.

Configurações do canal Email via SMTP/IMAP.

TODO: Implementar quando canal Email for desenvolvido.
Referência: WhatsApp settings em config/settings/whatsapp.py
"""

from __future__ import annotations

# from dataclasses import dataclass
# from functools import lru_cache
# import os


# @dataclass(frozen=True)
# class EmailSettings:
#     """Configurações do canal Email.
#
#     Attributes:
#         smtp_host: Host do servidor SMTP
#         smtp_port: Porta do servidor SMTP
#         smtp_username: Usuário SMTP
#         smtp_password: Senha SMTP
#         smtp_use_tls: Usar TLS
#         imap_host: Host do servidor IMAP (para recebimento)
#         imap_port: Porta do servidor IMAP
#         imap_username: Usuário IMAP
#         imap_password: Senha IMAP
#         from_email: Email de origem padrão
#         from_name: Nome de origem padrão
#         request_timeout_seconds: Timeout para conexões
#         max_retries: Máximo de tentativas em caso de erro
#     """
#
#     # SMTP (envio)
#     smtp_host: str = ""
#     smtp_port: int = 587
#     smtp_username: str = ""
#     smtp_password: str = ""
#     smtp_use_tls: bool = True
#
#     # IMAP (recebimento)
#     imap_host: str = ""
#     imap_port: int = 993
#     imap_username: str = ""
#     imap_password: str = ""
#
#     # Identidade
#     from_email: str = ""
#     from_name: str = ""
#
#     # Timeouts e retries
#     request_timeout_seconds: float = 30.0
#     max_retries: int = 3
#
#     def validate(self) -> list[str]:
#         """Valida configurações mínimas de Email."""
#         errors: list[str] = []
#         if not self.smtp_host:
#             errors.append("EMAIL_SMTP_HOST não configurado")
#         if not self.from_email:
#             errors.append("EMAIL_FROM_EMAIL não configurado")
#         return errors


# def _load_from_env() -> EmailSettings:
#     """Carrega EmailSettings de variáveis de ambiente."""
#     return EmailSettings(
#         smtp_host=os.getenv("EMAIL_SMTP_HOST", ""),
#         smtp_port=int(os.getenv("EMAIL_SMTP_PORT", "587")),
#         smtp_username=os.getenv("EMAIL_SMTP_USERNAME", ""),
#         smtp_password=os.getenv("EMAIL_SMTP_PASSWORD", ""),
#         smtp_use_tls=os.getenv("EMAIL_SMTP_USE_TLS", "true").lower() in ("true", "1"),
#         imap_host=os.getenv("EMAIL_IMAP_HOST", ""),
#         imap_port=int(os.getenv("EMAIL_IMAP_PORT", "993")),
#         imap_username=os.getenv("EMAIL_IMAP_USERNAME", ""),
#         imap_password=os.getenv("EMAIL_IMAP_PASSWORD", ""),
#         from_email=os.getenv("EMAIL_FROM_EMAIL", ""),
#         from_name=os.getenv("EMAIL_FROM_NAME", ""),
#         request_timeout_seconds=float(
#             os.getenv("EMAIL_REQUEST_TIMEOUT_SECONDS", "30")
#         ),
#         max_retries=int(os.getenv("EMAIL_MAX_RETRIES", "3")),
#     )


# @lru_cache(maxsize=1)
# def get_email_settings() -> EmailSettings:
#     """Retorna instância cacheada de EmailSettings."""
#     return _load_from_env()
