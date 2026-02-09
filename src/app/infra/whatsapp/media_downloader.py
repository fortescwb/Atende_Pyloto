"""Downloader de midia do WhatsApp (Graph API)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from config.settings import get_whatsapp_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MediaDownloadResult:
    """Resultado do download de mídia."""

    content: bytes | None
    mime_type: str | None
    error: str | None = None


class WhatsAppMediaDownloader:
    """Helper para baixar mídia via Graph API."""

    def __init__(self) -> None:
        self._settings = get_whatsapp_settings()
        self._timeout = min(self._settings.request_timeout_seconds, 30.0)

    async def download(
        self,
        *,
        media_id: str | None = None,
        media_url: str | None = None,
    ) -> MediaDownloadResult:
        """Baixa bytes de mídia via media_id ou media_url."""
        if not media_id and not media_url:
            return MediaDownloadResult(content=None, mime_type=None, error="missing_media_reference")

        max_retries = max(0, min(self._settings.max_retries, 2))
        for attempt in range(max_retries + 1):
            try:
                result = await self._attempt_download(media_id=media_id, media_url=media_url)
                if result is not None:
                    return result
            except httpx.TimeoutException:
                logger.warning(
                    "whatsapp_media_download_timeout",
                    extra={"attempt": attempt + 1},
                )
                if attempt >= max_retries:
                    return MediaDownloadResult(content=None, mime_type=None, error="timeout")
            except Exception as exc:
                logger.warning(
                    "whatsapp_media_download_failed",
                    extra={"error_type": type(exc).__name__, "attempt": attempt + 1},
                )
                if attempt >= max_retries:
                    return MediaDownloadResult(
                        content=None,
                        mime_type=None,
                        error="download_failed",
                    )

        return MediaDownloadResult(content=None, mime_type=None, error="download_failed")

    async def _attempt_download(
        self,
        *,
        media_id: str | None,
        media_url: str | None,
    ) -> MediaDownloadResult | None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            url, mime_type = await self._resolve_media_url(client, media_id, media_url)
            if not url:
                return MediaDownloadResult(content=None, mime_type=mime_type, error="media_url_unresolved")
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {self._settings.access_token}"},
            )
            response.raise_for_status()
            if self._is_too_large(response):
                return MediaDownloadResult(content=None, mime_type=mime_type, error="media_too_large")
            return MediaDownloadResult(content=response.content, mime_type=mime_type, error=None)

    def _is_too_large(self, response: httpx.Response) -> bool:
        content_length = response.headers.get("content-length")
        return bool(content_length and int(content_length) > self._settings.media_max_size_bytes)

    async def _resolve_media_url(
        self,
        client: httpx.AsyncClient,
        media_id: str | None,
        media_url: str | None,
    ) -> tuple[str | None, str | None]:
        if media_url:
            return media_url, None

        if not media_id:
            return None, None

        endpoint = f"{self._settings.api_endpoint}/{media_id}"
        headers = {"Authorization": f"Bearer {self._settings.access_token}"}
        response = await client.get(endpoint, headers=headers)
        response.raise_for_status()
        data = response.json()

        url = data.get("url") if isinstance(data, dict) else None
        mime_type = data.get("mime_type") if isinstance(data, dict) else None
        return url, mime_type
