"""Health and readiness endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from hermes_api.schemas import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])

_START_TIME = time.time()
VERSION = "0.1.0"


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns 200 when the service is alive.",
)
async def health() -> HealthResponse:
    """Liveness probe — returns immediately."""
    return HealthResponse(
        status="ok",
        version=VERSION,
        uptime_seconds=round(time.time() - _START_TIME, 2),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="Returns 200 when all dependencies are ready, 503 otherwise.",
)
async def readiness() -> JSONResponse:
    """Readiness probe — checks dependent subsystems."""
    checks: dict[str, bool] = {
        "api": True,
        # Future: "database": check_db(), "memory": check_memory()
    }
    ready = all(checks.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content=ReadinessResponse(ready=ready, checks=checks).model_dump(),
    )
