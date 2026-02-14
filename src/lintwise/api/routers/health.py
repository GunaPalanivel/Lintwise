"""Health check endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from lintwise.api.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check — confirms the service is running."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        services={
            "api": "running",
        },
    )


@router.get("/readiness", response_model=HealthResponse)
async def readiness_check() -> HealthResponse:
    """Readiness check — confirms the service can accept requests."""
    return HealthResponse(
        status="ready",
        version="0.1.0",
        services={
            "api": "ready",
        },
    )
