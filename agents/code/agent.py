"""Code agent — code generation, review, testing, and refactoring."""
from __future__ import annotations

from hermes_orchestrator.agent import BaseAgent
from hermes_orchestrator.schemas import AgentConfig, ToolCall, ToolResult


class CodeAgent(BaseAgent):
    """
    Specialized agent for software engineering tasks.

    Allowed tools: read_file, write_file, run_tests, lint, git_status, git_diff, search_code
    """

    ALLOWED_TOOLS: frozenset[str] = frozenset({
        "read_file",
        "write_file",
        "run_tests",
        "lint",
        "git_status",
        "git_diff",
        "search_code",
    })

    async def handle_tool(self, call: ToolCall) -> ToolResult:
        """Execute a verified tool call. Tools are wired via MCP in F4."""
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=False,
            error=f"Tool '{call.tool_name}' not yet wired to MCP backend",
        )


def make_code_agent() -> CodeAgent:
    """Factory: create a CodeAgent with default configuration."""
    config = AgentConfig(
        agent_id="code",
        model="claude-sonnet-4-6",
        allowed_tools=CodeAgent.ALLOWED_TOOLS,
        system_prompt=(
            "You are a code agent for the Hermes Agent OS. "
            "You write clean, typed, tested, and secure code. "
            "Follow the project's coding standards (Ruff + mypy for Python, strict TS). "
            "Never write secrets. Always add tests. Review your own output critically."
        ),
    )
    return CodeAgent(config=config)
