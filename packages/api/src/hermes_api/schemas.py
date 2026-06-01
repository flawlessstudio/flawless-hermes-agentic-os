"""API-level Pydantic schemas for request/response validation."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response from the /health endpoint."""

    status: str
    version: str
    uptime_seconds: float


class ReadinessResponse(BaseModel):
    """Response from the /ready endpoint."""

    ready: bool
    checks: dict[str, bool]


class AgentSummary(BaseModel):
    """Summary representation of a registered agent."""

    agent_id: str
    model: str
    allowed_tools: list[str]


class AgentRunRequest(BaseModel):
    """Request body for POST /agents/{agent_id}/run."""

    message: str
    reset_history: bool = False


class AgentRunResponse(BaseModel):
    """Response from POST /agents/{agent_id}/run."""

    agent_id: str
    response: str
    request_id: str = Field(default_factory=lambda: str(uuid4()))


class MemorySearchRequest(BaseModel):
    """Request body for POST /memory/search."""

    agent_id: str
    query: str
    n: int = 10
    where: dict[str, Any] | None = None


class MemoryRememberRequest(BaseModel):
    """Request body for POST /memory/remember."""

    agent_id: str
    text: str
    metadata: dict[str, Any] | None = None


class MemoryRememberResponse(BaseModel):
    """Response from POST /memory/remember."""

    entry_id: str


class ErrorResponse(BaseModel):
    """Standard error response body."""

    error: str
    request_id: str | None = None
    detail: str | None = None
