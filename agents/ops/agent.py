"""Ops agent — system health, CI/CD, deployment, and monitoring."""

from __future__ import annotations

import asyncio
import os
import platform
import sys
from datetime import UTC, datetime
from typing import Any

import structlog

from hermes_orchestrator.agent import BaseAgent
from hermes_orchestrator.schemas import AgentConfig, ToolCall, ToolResult

log = structlog.get_logger(__name__)


class OpsAgent(BaseAgent):
    """
    Specialized agent for DevOps and system operations.

    Allowed tools: health_check, get_logs, get_metrics, list_deployments
    Note: Destructive operations require PAUSA HUMANA confirmation.
    """

    ALLOWED_TOOLS: frozenset[str] = frozenset(
        {
            "health_check",
            "get_logs",
            "get_metrics",
            "list_deployments",
        }
    )

    TOOL_SCHEMAS: list[dict[str, Any]] = [  # noqa: RUF012
        {
            "name": "health_check",
            "description": "Check system health: Python version, env vars presence, disk space.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_logs",
            "description": "Read the last N lines of a log file.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Log file path."},
                    "lines": {"type": "integer", "default": 50},
                },
                "required": ["path"],
            },
        },
        {
            "name": "get_metrics",
            "description": "Return basic process/system metrics.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "list_deployments",
            "description": "List running Docker containers (read-only).",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
    ]

    async def handle_tool(self, call: ToolCall) -> ToolResult:
        """Execute a verified tool call (read-only ops)."""
        try:
            if call.tool_name == "health_check":
                return await self._health_check(call)
            if call.tool_name == "get_logs":
                return await self._get_logs(call)
            if call.tool_name == "get_metrics":
                return await self._get_metrics(call)
            if call.tool_name == "list_deployments":
                return await self._list_deployments(call)
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Tool '{call.tool_name}' not implemented in OpsAgent",
            )
        except Exception as exc:
            log.error("ops_agent.tool_error", tool=call.tool_name, error=str(exc))
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=str(exc),
            )

    async def _health_check(self, call: ToolCall) -> ToolResult:
        required_vars = [
            "ANTHROPIC_API_KEY",
            "HERMES_CLAUDE_MODEL",
        ]
        optional_vars = ["EXA_API_KEY", "GITHUB_PERSONAL_ACCESS_TOKEN", "SUPABASE_URL"]

        status: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "python": sys.version,
            "platform": platform.platform(),
            "env": {
                var: ("set" if os.environ.get(var) else "MISSING") for var in required_vars
            },
            "optional_env": {
                var: ("set" if os.environ.get(var) else "not set") for var in optional_vars
            },
        }

        missing = [k for k, v in status["env"].items() if v == "MISSING"]
        if missing:
            status["status"] = "degraded"
            status["missing_required"] = missing
        else:
            status["status"] = "healthy"

        import json

        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=json.dumps(status, indent=2),
        )

    async def _get_logs(self, call: ToolCall) -> ToolResult:
        from pathlib import Path

        path = Path(call.arguments["path"])
        n = int(call.arguments.get("lines", 50))
        if not path.exists():
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Log file not found: {path}",
            )
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = "\n".join(lines[-n:])
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=tail,
        )

    async def _get_metrics(self, call: ToolCall) -> ToolResult:
        import json

        try:
            import psutil  # type: ignore[import-untyped]

            metrics = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
            }
        except ImportError:
            metrics = {"note": "psutil not installed — install for full metrics"}

        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=json.dumps(metrics, indent=2),
        )

    async def _list_deployments(self, call: ToolCall) -> ToolResult:
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "ps",
            "--format",
            "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace")
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"docker ps failed: {err}",
            )
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=stdout.decode("utf-8", errors="replace"),
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
