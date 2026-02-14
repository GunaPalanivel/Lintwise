"""Middleware — CORS, request logging, error handling."""

from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from lintwise.core.exceptions import (
    GitHubAuthError,
    GitHubRateLimitError,
    InvalidPRURLError,
    LLMError,
    LintwiseError,
    PRNotFoundError,
    ValidationError,
)
from lintwise.core.logging import get_logger

logger = get_logger(__name__)


def setup_middleware(app: FastAPI) -> None:
    """Attach all middleware to the FastAPI app."""

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        """Log every request with timing and a correlation ID."""
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter_ns()

        response = await call_next(request)

        duration_ms = (time.perf_counter_ns() - start) // 1_000_000
        logger.info(
            "http_request",
            method=request.method,
            path=str(request.url.path),
            status=response.status_code,
            duration_ms=duration_ms,
            request_id=request_id,
        )
        response.headers["X-Request-ID"] = request_id
        return response


def setup_exception_handlers(app: FastAPI) -> None:
    """Register domain exception → HTTP response mappings."""

    @app.exception_handler(InvalidPRURLError)
    async def handle_invalid_pr_url(request: Request, exc: InvalidPRURLError):
        return JSONResponse(status_code=400, content={"error": "Invalid PR URL", "detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def handle_validation(request: Request, exc: ValidationError):
        return JSONResponse(status_code=422, content={"error": "Validation Error", "detail": str(exc)})

    @app.exception_handler(GitHubAuthError)
    async def handle_auth(request: Request, exc: GitHubAuthError):
        return JSONResponse(status_code=401, content={"error": "GitHub Auth Error", "detail": str(exc)})

    @app.exception_handler(PRNotFoundError)
    async def handle_not_found(request: Request, exc: PRNotFoundError):
        return JSONResponse(status_code=404, content={"error": "PR Not Found", "detail": str(exc)})

    @app.exception_handler(GitHubRateLimitError)
    async def handle_rate_limit(request: Request, exc: GitHubRateLimitError):
        return JSONResponse(status_code=429, content={"error": "Rate Limited", "detail": str(exc)})

    @app.exception_handler(LLMError)
    async def handle_llm(request: Request, exc: LLMError):
        return JSONResponse(status_code=502, content={"error": "LLM Error", "detail": str(exc)})

    @app.exception_handler(LintwiseError)
    async def handle_lintwise(request: Request, exc: LintwiseError):
        return JSONResponse(status_code=500, content={"error": "Internal Error", "detail": str(exc)})
