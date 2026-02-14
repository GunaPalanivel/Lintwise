"""Retry logic with exponential backoff."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from lintwise.core.exceptions import LLMRateLimitError
from lintwise.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


async def retry_with_backoff(
    func: Callable[..., Coroutine[Any, Any, T]],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: tuple[type[Exception], ...] = (LLMRateLimitError,),
    **kwargs: Any,
) -> T:
    """Execute an async function with exponential backoff retry.

    Args:
        func: Async callable to execute.
        max_retries: Maximum number of retries (not counting the initial attempt).
        base_delay: Base delay in seconds.
        max_delay: Maximum delay between retries.
        retryable_exceptions: Tuple of exception types that trigger a retry.

    Returns:
        Return value of the function.

    Raises:
        The last exception if all retries fail.
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as e:
            last_exception = e
            if attempt >= max_retries:
                logger.error(
                    "retry_exhausted",
                    function=func.__name__,
                    attempts=attempt + 1,
                    error=str(e),
                )
                raise

            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(
                "retrying",
                function=func.__name__,
                attempt=attempt + 1,
                max_retries=max_retries,
                delay=delay,
                error=str(e),
            )
            await asyncio.sleep(delay)

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected retry loop exit")
