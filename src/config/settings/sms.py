"""Settings específicas de SMS.

Configurações do canal SMS via provedores (Twilio, AWS SNS, etc).

TODO: Implementar quando canal SMS for desenvolvido.
Referência: WhatsApp settings em config/settings/whatsapp.py
"""

from __future__ import annotations

# from dataclasses import dataclass
# from functools import lru_cache
# import os
# from typing import Literal

# SmsProvider = Literal["twilio", "aws_sns", "vonage"]


# @dataclass(frozen=True)
# class SmsSettings:
#     """Configurações do canal SMS.
#
#     Attributes:
#         provider: Provedor de SMS (twilio, aws_sns, vonage)
#         account_sid: Account SID (Twilio)
#         auth_token: Auth Token (Twilio)
#         from_number: Número de origem
#         aws_region: Região AWS (para SNS)
#         aws_access_key_id: Access Key AWS (para SNS)
#         aws_secret_access_key: Secret Key AWS (para SNS)
#         request_timeout_seconds: Timeout para requisições
#         max_retries: Máximo de tentativas em caso de erro
#     """
#
#     # Provedor
#     provider: SmsProvider = "twilio"
#
#     # Twilio
#     account_sid: str = ""
#     auth_token: str = ""
#     from_number: str = ""
#
#     # AWS SNS
#     aws_region: str = "us-east-1"
#     aws_access_key_id: str = ""
#     aws_secret_access_key: str = ""
#
#     # Timeouts e retries
#     request_timeout_seconds: float = 30.0
#     max_retries: int = 3
#
#     def validate(self) -> list[str]:
#         """Valida configurações mínimas de SMS."""
#         errors: list[str] = []
#
#         if self.provider == "twilio":
#             if not self.account_sid:
#                 errors.append("SMS_ACCOUNT_SID não configurado")
#             if not self.auth_token:
#                 errors.append("SMS_AUTH_TOKEN não configurado")
#             if not self.from_number:
#                 errors.append("SMS_FROM_NUMBER não configurado")
#         elif self.provider == "aws_sns":
#             if not self.aws_access_key_id:
#                 errors.append("SMS_AWS_ACCESS_KEY_ID não configurado")
#
#         return errors


# def _load_from_env() -> SmsSettings:
#     """Carrega SmsSettings de variáveis de ambiente."""
#     provider_str = os.getenv("SMS_PROVIDER", "twilio").lower()
#     provider: SmsProvider = (
#         provider_str if provider_str in ("twilio", "aws_sns", "vonage") else "twilio"
#     )
#
#     return SmsSettings(
#         provider=provider,
#         account_sid=os.getenv("SMS_ACCOUNT_SID", ""),
#         auth_token=os.getenv("SMS_AUTH_TOKEN", ""),
#         from_number=os.getenv("SMS_FROM_NUMBER", ""),
#         aws_region=os.getenv("SMS_AWS_REGION", "us-east-1"),
#         aws_access_key_id=os.getenv("SMS_AWS_ACCESS_KEY_ID", ""),
#         aws_secret_access_key=os.getenv("SMS_AWS_SECRET_ACCESS_KEY", ""),
#         request_timeout_seconds=float(
#             os.getenv("SMS_REQUEST_TIMEOUT_SECONDS", "30")
#         ),
#         max_retries=int(os.getenv("SMS_MAX_RETRIES", "3")),
#     )


# @lru_cache(maxsize=1)
# def get_sms_settings() -> SmsSettings:
#     """Retorna instância cacheada de SmsSettings."""
#     return _load_from_env()
