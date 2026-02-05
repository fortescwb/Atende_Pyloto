"""Testes para TranscriptionAgent."""

from __future__ import annotations

import pytest

from app.infra.whatsapp.media_downloader import MediaDownloadResult
from app.protocols.transcription_service import TranscriptionResult
from app.services.transcription_agent import TranscriptionAgent


class FakeDownloader:
    def __init__(self, result: MediaDownloadResult):
        self._result = result

    async def download(self, *, media_id: str | None = None, media_url: str | None = None):
        return self._result


class FakeWhisper:
    def __init__(self, result: TranscriptionResult):
        self._result = result

    async def transcribe(self, *, audio_bytes: bytes, mime_type: str | None = None):
        return self._result


@pytest.mark.asyncio
async def test_transcription_success() -> None:
    downloader = FakeDownloader(MediaDownloadResult(content=b"data", mime_type="audio/ogg"))
    whisper = FakeWhisper(
        TranscriptionResult(
            text="Ola",
            language="pt",
            duration_seconds=1.2,
            confidence=0.9,
        )
    )
    agent = TranscriptionAgent(downloader=downloader, whisper_client=whisper)

    result = await agent.transcribe_whatsapp_audio(media_id="mid", wa_id="123")
    assert result.text == "Ola"
    assert result.confidence == 0.9


@pytest.mark.asyncio
async def test_transcription_download_failure_returns_fallback() -> None:
    downloader = FakeDownloader(MediaDownloadResult(content=None, mime_type=None, error="timeout"))
    whisper = FakeWhisper(TranscriptionResult(text="nao", confidence=0.9))
    agent = TranscriptionAgent(downloader=downloader, whisper_client=whisper)

    result = await agent.transcribe_whatsapp_audio(media_id="mid", wa_id="123")
    assert result.confidence == 0.0
    assert result.error == "timeout"


@pytest.mark.asyncio
async def test_transcription_whisper_error_returns_fallback() -> None:
    downloader = FakeDownloader(MediaDownloadResult(content=b"data", mime_type="audio/ogg"))
    whisper = FakeWhisper(TranscriptionResult(text="", confidence=0.0, error="whisper_failed"))
    agent = TranscriptionAgent(downloader=downloader, whisper_client=whisper)

    result = await agent.transcribe_whatsapp_audio(media_id="mid", wa_id="123")
    assert result.confidence == 0.0
    assert result.error == "whisper_failed"
