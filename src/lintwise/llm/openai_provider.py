"""OpenAI LLM provider implementation."""

from __future__ import annotations

from typing import Any

import tiktoken
from openai import AsyncOpenAI

from lintwise.core.config import Settings
from lintwise.core.exceptions import (
    LLMContextOverflowError,
    LLMError,
    LLMRateLimitError,
    LLMResponseParseError,
)
from lintwise.core.logging import get_logger
from lintwise.llm.base import LLMProvider, LLMResponse

logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI / GPT-4 LLM adapter using the official async client."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
        )
        self._model = settings.openai_model
        self._default_temp = settings.openai_temperature
        self._default_max_tokens = settings.openai_max_tokens

        # Tokenizer (best-effort: fall back to cl100k_base for unknown models)
        try:
            self._encoding = tiktoken.encoding_for_model(self._model)
        except KeyError:
            self._encoding = tiktoken.get_encoding("cl100k_base")

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Send a chat completion to OpenAI.

        Handles rate limits, context overflow, and malformed responses.
        """
        temp = temperature if temperature is not None else self._default_temp
        max_tok = max_tokens if max_tokens is not None else self._default_max_tokens

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tok,
        }

        if response_format:
            kwargs["response_format"] = response_format

        try:
            response = await self._client.chat.completions.create(**kwargs)
        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str or "429" in error_str:
                raise LLMRateLimitError(f"OpenAI rate limit: {e}") from e
            if "context" in error_str or "maximum" in error_str or "token" in error_str:
                raise LLMContextOverflowError(f"Context overflow: {e}") from e
            raise LLMError(f"OpenAI API error: {e}") from e

        choice = response.choices[0] if response.choices else None
        if not choice or not choice.message.content:
            raise LLMResponseParseError("Empty response from OpenAI")

        usage = response.usage
        return LLMResponse(
            content=choice.message.content,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            model=response.model or self._model,
        )

    async def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken."""
        return len(self._encoding.encode(text))

    async def close(self) -> None:
        """Close the async client."""
        await self._client.close()
