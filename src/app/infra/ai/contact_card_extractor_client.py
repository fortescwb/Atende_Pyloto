"""Cliente OpenAI para ContactCardExtractor.

Implementacao de IO — pertence a app/infra conforme REGRAS § 2.3.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from ai.utils._json_extractor import extract_json_from_response
from config.settings.ai.openai import OpenAISettings, get_openai_settings

logger = logging.getLogger(__name__)


class ContactCardExtractorClient:
    """Cliente LLM para extracao de patch do ContactCard."""

    __slots__ = ("_client", "_model", "_timeout_seconds")

    def __init__(
        self,
        *,
        settings: OpenAISettings | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        client: AsyncOpenAI | None = None,
    ) -> None:
        cfg = settings or get_openai_settings()
        self._model = model or cfg.model or "gpt-4o-mini"
        # Timeout curto conforme requisito (5-8s)
        self._timeout_seconds = float(timeout_seconds or min(cfg.timeout_seconds, 8.0))
        if client is not None:
            self._client = client
        else:
            self._client = AsyncOpenAI(
                api_key=api_key or cfg.api_key,
                timeout=self._timeout_seconds,
            )

    async def extract(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any] | None:
        """Executa chamada OpenAI e retorna JSON parseado."""
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=400,
            )
        except Exception as exc:
            logger.warning(
                "contact_card_extractor_openai_error",
                extra={"error_type": type(exc).__name__},
            )
            return None

        content = None
        try:
            content = response.choices[0].message.content if response.choices else None
        except Exception:
            content = None

        if not content:
            logger.warning("contact_card_extractor_empty_response")
            return None

        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        extracted = extract_json_from_response(content)
        if extracted is None:
            logger.warning("contact_card_extractor_parse_failed")
        return extracted
