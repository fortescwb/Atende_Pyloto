"""Cliente HTTP base para conectores da camada API."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class HttpClientConfig:
    """Configuração do cliente HTTP."""

    timeout_seconds: float = 30.0
    max_retries: int = 3
    backoff_base_seconds: float = 2.0
    backoff_max_seconds: float = 30.0
    default_headers: dict[str, str] = field(default_factory=dict)
    verify_ssl: bool = True


class HttpError(Exception):
    """Erro de requisição HTTP sem dados sensíveis."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        is_retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.is_retryable = is_retryable


class HttpClient:
    """Cliente HTTP simples para chamadas externas."""

    def __init__(self, config: HttpClientConfig | None = None) -> None:
        self._config = config or HttpClientConfig()

    async def post(
        self,
        url: str,
        json: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        merged_headers = {**self._config.default_headers, **(headers or {})}
        for attempt in range(self._config.max_retries + 1):
            try:
                async with httpx.AsyncClient(verify=self._config.verify_ssl) as client:
                    response = await client.post(
                        url,
                        json=json,
                        headers=merged_headers,
                        timeout=self._config.timeout_seconds,
                    )
                if response.status_code in (429,) or response.status_code >= 500:
                    raise HttpError(
                        "http_retryable_status",
                        status_code=response.status_code,
                        is_retryable=True,
                    )
                return response
            except HttpError as exc:
                if not exc.is_retryable or attempt >= self._config.max_retries:
                    raise
                await _backoff_sleep(
                    attempt,
                    self._config.backoff_base_seconds,
                    self._config.backoff_max_seconds,
                )
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                if attempt >= self._config.max_retries:
                    raise HttpError("http_connection_error", is_retryable=True) from exc
                await _backoff_sleep(
                    attempt,
                    self._config.backoff_base_seconds,
                    self._config.backoff_max_seconds,
                )
        raise HttpError("http_retry_exhausted", is_retryable=True)


async def _backoff_sleep(attempt: int, base: float, max_seconds: float) -> None:
    backoff = min((2**attempt) * base, max_seconds)
    logger.info("http_backoff", extra={"backoff_seconds": backoff})
    await asyncio.sleep(backoff)
