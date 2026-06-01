"""Ops agent — system health, CI/CD, deployment, and monitoring."""
from __future__ import annotations

from hermes_orchestrator.agent import BaseAgent
from hermes_orchestrator.schemas import AgentConfig, ToolCall, ToolResult


class OpsAgent(BaseAgent):
    """
    Specialized agent for DevOps and system operations.

    Allowed tools: health_check, get_logs, get_metrics, list_deployments
    Note: Destructive operations require PAUSA HUMANA confirmation.
    """

    ALLOWED_TOOLS: frozenset[str] = frozenset({
        "health_check",
        "get_logs",
        "get_metrics",
        "list_deployments",
    })

    async def handle_tool(self, call: ToolCall) -> ToolResult:
        """Execute a verified tool call. Tools are wired via MCP in F4."""
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=False,
            error=f"Tool '{call.tool_name}' not yet wired to MCP backend",
        )


def make_ops_agent() -> OpsAgent:
    """Factory: create an OpsAgent with default configuration."""
    config = AgentConfig(
        agent_id="ops",
        model="claude-sonnet-4-6",
        allowed_tools=OpsAgent.ALLOWED_TOOLS,
        system_prompt=(
            "You are an ops agent for the Hermes Agent OS. "
            "Monitor system health, surface issues, and coordinate deployments. "
            "NEVER trigger destructive operations without explicit human confirmation. "
            "Escalate anomalies immediately."
        ),
    )
    return OpsAgent(config=config)
