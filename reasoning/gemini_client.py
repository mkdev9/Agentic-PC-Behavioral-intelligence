"""
desktop_agent.reasoning.gemini_client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Async interface to the Google Gemini API using the new ``google-genai`` SDK
with streaming support, thinking config, and retry logic.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from google import genai
from google.genai import types

from utils.helpers import retry

logger = logging.getLogger(__name__)


class GeminiClient:
    """Wrapper around the ``google-genai`` Client for text generation."""

    def __init__(self, config: dict[str, Any]) -> None:
        llm_cfg = config.get("llm", {})
        api_key: str = llm_cfg.get("api_key", "")
        if not api_key:
            raise ValueError(
                "Gemini API key is not set. Add it to config/settings.yaml "
                "or export GEMINI_API_KEY as an environment variable."
            )

        self._client = genai.Client(api_key=api_key)
        self._model: str = llm_cfg.get("model", "gemini-3-flash-preview")
        self._temperature: float = llm_cfg.get("temperature", 0.7)
        self._max_output_tokens: int = llm_cfg.get("max_output_tokens", 1024)

        logger.info(
            "GeminiClient initialised — model=%s, temp=%.1f",
            self._model,
            self._temperature,
        )

    @retry(max_attempts=3, backoff_base=2.0, exceptions=(Exception,))
    async def generate(self, prompt: str) -> str:
        """Send *prompt* to Gemini and return the generated text.

        The blocking SDK call is off-loaded to a thread so the event loop
        stays responsive.
        """
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, self._blocking_generate, prompt)
        logger.debug("Gemini response received — %d chars", len(text))
        return text

    def _blocking_generate(self, prompt: str) -> str:
        """Synchronous generate call (runs inside executor).

        Uses streaming to collect the full response.
        """
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ]

        generate_config = types.GenerateContentConfig(
            temperature=self._temperature,
            max_output_tokens=self._max_output_tokens,
        )

        chunks: list[str] = []
        for chunk in self._client.models.generate_content_stream(
            model=self._model,
            contents=contents,
            config=generate_config,
        ):
            if chunk.text:
                chunks.append(chunk.text)

        return "".join(chunks).strip()
