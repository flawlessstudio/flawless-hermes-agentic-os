"""Memory management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from hermes_api.schemas import (
    MemoryRememberRequest,
    MemoryRememberResponse,
    MemorySearchRequest,
)
from hermes_memory.schemas import MemoryQueryResult

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post(
    "/remember",
    response_model=MemoryRememberResponse,
    summary="Store a memory",
)
async def remember(body: MemoryRememberRequest, request: Request) -> MemoryRememberResponse:
    """Store a piece of text in vector memory for an agent."""
    memory_manager = request.app.state.memory_manager
    entry_id = memory_manager.remember(
        agent_id=body.agent_id,
        text=body.text,
        metadata=body.metadata,
    )
    return MemoryRememberResponse(entry_id=entry_id)


@router.post(
    "/search",
    response_model=list[MemoryQueryResult],
    summary="Semantic search over memories",
)
async def search_memory(body: MemorySearchRequest, request: Request) -> list[MemoryQueryResult]:
    """Perform a semantic similarity search over an agent's memories."""
    memory_manager = request.app.state.memory_manager
    results = memory_manager.recall(
        agent_id=body.agent_id,
        query=body.query,
        n=body.n,
        where=body.where,
    )
    return results


@router.get(
    "/{agent_id}/count",
    summary="Memory count for an agent",
)
async def memory_count(agent_id: str, request: Request) -> dict[str, int]:
    """Return the number of stored memories for *agent_id*."""
    memory_manager = request.app.state.memory_manager
    return {"agent_id": agent_id, "count": memory_manager.memory_count(agent_id)}
