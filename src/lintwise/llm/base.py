"""Abstract LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Structured response from an LLM call."""

    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""


class LLMProvider(ABC):
    """Abstract base for LLM provider implementations.

    All providers implement the same interface so they can be swapped
    via configuration without code changes.
    """

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            temperature: Sampling temperature (0.0 = deterministic).
            max_tokens: Max tokens in the response.
            response_format: Optional format spec (e.g. {"type": "json_object"}).

        Returns:
            LLMResponse with content and token usage.
        """
        ...

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """Count tokens in the given text.

        Used for context window management and diff chunking.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release any held resources."""
        ...
