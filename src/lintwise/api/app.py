"""FastAPI application factory with lifespan management."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from lintwise.api.middleware import setup_exception_handlers, setup_middleware
from lintwise.api.routers import health, reviews, webhooks
from lintwise.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    This is the factory function used by uvicorn:
        uvicorn lintwise.api.app:create_app --factory --reload
    """
    setup_logging()

    app = FastAPI(
        title="Lintwise",
        description="AI-Powered GitHub PR Review Agent — multi-agent analysis with structured feedback",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middleware
    setup_middleware(app)
    setup_exception_handlers(app)

    # API Routes (prefixed with /api/v1)
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(reviews.router, prefix="/api/v1")
    app.include_router(webhooks.router, prefix="/api/v1")

    @app.get("/", include_in_schema=False)
    async def root():
        """Root redirect to docs."""
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/docs")

    logger.info("app_created", version="0.1.0")
    return app
