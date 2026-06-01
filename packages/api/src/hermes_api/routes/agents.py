"""Agent management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from hermes_api.schemas import AgentRunRequest, AgentRunResponse, AgentSummary

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get(
    "/",
    response_model=list[AgentSummary],
    summary="List registered agents",
)
async def list_agents(request: Request) -> list[AgentSummary]:
    """Return all currently registered agents."""
    registry = request.app.state.registry
    summaries: list[AgentSummary] = []
    for agent_id in registry.list_ids():
        agent = registry.get(agent_id)
        if agent is None:
            continue
        summaries.append(
            AgentSummary(
                agent_id=agent_id,
                model=agent.config.model,
                allowed_tools=sorted(agent.config.allowed_tools or agent.ALLOWED_TOOLS),
            )
        )
    return summaries


@router.get(
    "/{agent_id}",
    response_model=AgentSummary,
    summary="Get a specific agent",
)
async def get_agent(agent_id: str, request: Request) -> AgentSummary:
    """Retrieve metadata for a single agent."""
    registry = request.app.state.registry
    agent = registry.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id!r} not found")
    return AgentSummary(
        agent_id=agent_id,
        model=agent.config.model,
        allowed_tools=sorted(agent.config.allowed_tools or agent.ALLOWED_TOOLS),
    )


@router.post(
    "/{agent_id}/run",
    response_model=AgentRunResponse,
    summary="Run an agent turn",
)
async def run_agent(
    agent_id: str,
    body: AgentRunRequest,
    request: Request,
) -> AgentRunResponse:
    """Send a message to an agent and return its response."""
    registry = request.app.state.registry
    agent = registry.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id!r} not found")

    if body.reset_history:
        agent.reset()

    response_text = await agent.run(body.message)
    request_id = getattr(request.state, "request_id", None)

    return AgentRunResponse(
        agent_id=agent_id,
        response=response_text,
        request_id=request_id or "",
    )
