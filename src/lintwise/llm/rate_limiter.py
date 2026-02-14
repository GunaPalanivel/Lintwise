"""Token-aware rate limiter for LLM API calls."""

from __future__ import annotations

import asyncio
import time

from lintwise.core.logging import get_logger

logger = get_logger(__name__)


class TokenBucketRateLimiter:
    """Async rate limiter using the token-bucket algorithm.

    Supports both requests-per-minute (RPM) and tokens-per-minute (TPM).
    Also provides a concurrency semaphore.
    """

    def __init__(
        self,
        rpm: int = 60,
        tpm: int = 150_000,
        max_concurrent: int = 4,
    ) -> None:
        self._rpm = rpm
        self._tpm = tpm
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # Token buckets
        self._request_tokens = float(rpm)
        self._token_tokens = float(tpm)
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        """Refill buckets based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._last_refill = now

        # Refill proportionally (per minute → per second)
        self._request_tokens = min(self._rpm, self._request_tokens + elapsed * self._rpm / 60)
        self._token_tokens = min(self._tpm, self._token_tokens + elapsed * self._tpm / 60)

    async def acquire(self, estimated_tokens: int = 1000) -> None:
        """Wait until a request can proceed.

        Args:
            estimated_tokens: Estimated token usage for this request.
        """
        while True:
            self._refill()

            if self._request_tokens >= 1 and self._token_tokens >= estimated_tokens:
                self._request_tokens -= 1
                self._token_tokens -= estimated_tokens
                break

            # Wait proportionally to how many tokens we need
            wait_time = max(0.1, min(5.0, estimated_tokens / (self._tpm / 60)))
            await asyncio.sleep(wait_time)

        await self._semaphore.acquire()

    def release(self) -> None:
        """Release the concurrency semaphore after a request completes."""
        self._semaphore.release()

    async def __aenter__(self) -> TokenBucketRateLimiter:
        await self.acquire()
        return self

    async def __aexit__(self, *args: object) -> None:
        self.release()
