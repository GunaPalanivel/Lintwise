"""Tests for lintwise.llm — base interface and rate limiter."""

from __future__ import annotations

import asyncio

import pytest

from lintwise.llm.base import LLMProvider, LLMResponse
from lintwise.llm.rate_limiter import TokenBucketRateLimiter


# ── LLMResponse ─────────────────────────────────────────────────────────────


class TestLLMResponse:
    def test_creation(self):
        r = LLMResponse(content="Hello", prompt_tokens=10, completion_tokens=5, model="gpt-4o")
        assert r.content == "Hello"
        assert r.prompt_tokens == 10
        assert r.completion_tokens == 5
        assert r.model == "gpt-4o"

    def test_defaults(self):
        r = LLMResponse(content="Hi")
        assert r.prompt_tokens == 0
        assert r.completion_tokens == 0
        assert r.model == ""

    def test_serialization(self):
        r = LLMResponse(content="Test", prompt_tokens=100)
        data = r.model_dump()
        restored = LLMResponse.model_validate(data)
        assert restored.content == "Test"


# ── LLMProvider Interface ──────────────────────────────────────────────────


class TestLLMProviderInterface:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            LLMProvider()

    def test_concrete_implementation(self):
        class MockProvider(LLMProvider):
            async def complete(self, messages, **kwargs):
                return LLMResponse(content="mock")
            async def count_tokens(self, text):
                return len(text)
            async def close(self):
                pass

        provider = MockProvider()
        assert provider is not None


# ── Rate Limiter ────────────────────────────────────────────────────────────


class TestTokenBucketRateLimiter:
    @pytest.mark.asyncio
    async def test_acquire_release(self):
        limiter = TokenBucketRateLimiter(rpm=100, tpm=100000, max_concurrent=2)
        await limiter.acquire(estimated_tokens=100)
        limiter.release()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        limiter = TokenBucketRateLimiter(rpm=100, tpm=100000, max_concurrent=2)
        async with limiter:
            pass  # Should not raise

    @pytest.mark.asyncio
    async def test_concurrency_limit(self):
        limiter = TokenBucketRateLimiter(rpm=1000, tpm=1000000, max_concurrent=2)
        acquired = 0

        async def worker():
            nonlocal acquired
            async with limiter:
                acquired += 1
                await asyncio.sleep(0.01)

        tasks = [asyncio.create_task(worker()) for _ in range(5)]
        await asyncio.gather(*tasks)
        assert acquired == 5  # All should complete eventually

    def test_initialization(self):
        limiter = TokenBucketRateLimiter(rpm=60, tpm=150000, max_concurrent=4)
        assert limiter._rpm == 60
        assert limiter._tpm == 150000
