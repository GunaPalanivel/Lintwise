"""Comprehensive tests for lintwise.orchestrator.retry."""

from __future__ import annotations

import pytest

from lintwise.core.exceptions import LLMRateLimitError
from lintwise.orchestrator.retry import retry_with_backoff


class TestRetryWithBackoff:
    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await retry_with_backoff(func, max_retries=3, base_delay=0.01)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_retryable_error(self):
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise LLMRateLimitError("rate limit")
            return "success"

        result = await retry_with_backoff(func, max_retries=3, base_delay=0.01)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        async def func():
            raise LLMRateLimitError("always fails")

        with pytest.raises(LLMRateLimitError):
            await retry_with_backoff(func, max_retries=2, base_delay=0.01)

    @pytest.mark.asyncio
    async def test_non_retryable_error_not_retried(self):
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            await retry_with_backoff(func, max_retries=3, base_delay=0.01)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_passes_args_and_kwargs(self):
        async def func(a, b, c=None):
            return (a, b, c)

        result = await retry_with_backoff(func, 1, 2, c="three", max_retries=0, base_delay=0.01)
        assert result == (1, 2, "three")

    @pytest.mark.asyncio
    async def test_custom_retryable_exceptions(self):
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("custom retryable")
            return "ok"

        result = await retry_with_backoff(
            func,
            max_retries=3,
            base_delay=0.01,
            retryable_exceptions=(ValueError,),
        )
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_zero_retries(self):
        async def func():
            raise LLMRateLimitError("fail")

        with pytest.raises(LLMRateLimitError):
            await retry_with_backoff(func, max_retries=0, base_delay=0.01)
