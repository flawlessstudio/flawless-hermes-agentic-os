"""Code agent — code generation, review, testing, and refactoring."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import structlog

from hermes_orchestrator.agent import BaseAgent
from hermes_orchestrator.schemas import AgentConfig, ToolCall, ToolResult

log = structlog.get_logger(__name__)

# Hard limit on paths the code agent may write to (no system paths)
_SAFE_WRITE_ROOTS = frozenset(
    {
        "packages",
        "agents",
        "apps",
        "tests",
        "scripts",
    }
)


def _is_safe_write_path(path: Path) -> bool:
    """Return True only if path starts with an allowed root directory."""
    try:
        parts = path.parts
        return bool(parts) and parts[0] in _SAFE_WRITE_ROOTS
    except Exception:
        return False


class CodeAgent(BaseAgent):
    """
    Specialized agent for software engineering tasks.

    Allowed tools: read_file, write_file, run_tests, lint, git_status, git_diff, search_code
    """

    ALLOWED_TOOLS: frozenset[str] = frozenset(
        {
            "read_file",
            "write_file",
            "run_tests",
            "lint",
            "git_status",
            "git_diff",
            "search_code",
        }
    )

    TOOL_SCHEMAS: list[dict[str, Any]] = [  # noqa: RUF012
        {
            "name": "read_file",
            "description": "Read a source file.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
        {
            "name": "write_file",
            "description": "Write content to a file (restricted to safe project roots).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
        {
            "name": "run_tests",
            "description": "Run pytest on the packages directory.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "lint",
            "description": "Run ruff lint check on packages and agents.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "git_status",
            "description": "Show git status of the working tree.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "git_diff",
            "description": "Show git diff of staged or unstaged changes.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "staged": {"type": "boolean", "default": False},
                    "path": {"type": "string", "description": "Optional path to diff."},
                },
                "required": [],
            },
        },
        {
            "name": "search_code",
            "description": "Search for a pattern in source files using grep.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "directory": {"type": "string", "default": "."},
                },
                "required": ["pattern"],
            },
        },
    ]

    async def handle_tool(self, call: ToolCall) -> ToolResult:
        """Execute a verified tool call."""
        try:
            if call.tool_name == "read_file":
                return await self._read_file(call)
            if call.tool_name == "write_file":
                return await self._write_file(call)
            if call.tool_name == "run_tests":
                return await self._run_subprocess(call, ["uv", "run", "pytest", "--tb=short", "-q"])
            if call.tool_name == "lint":
                return await self._run_subprocess(
                    call, ["uv", "run", "ruff", "check", "packages", "agents"]
                )
            if call.tool_name == "git_status":
                return await self._run_subprocess(call, ["git", "status", "--short"])
            if call.tool_name == "git_diff":
                cmd = ["git", "diff"]
                if call.arguments.get("staged"):
                    cmd.append("--staged")
                if call.arguments.get("path"):
                    cmd.append(call.arguments["path"])
                return await self._run_subprocess(call, cmd)
            if call.tool_name == "search_code":
                pattern = call.arguments["pattern"]
                directory = call.arguments.get("directory", ".")
                return await self._run_subprocess(
                    call,
                    ["grep", "-rn", "--include=*.py", "--include=*.ts", pattern, directory],
                )
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Tool '{call.tool_name}' not implemented in CodeAgent",
            )
        except Exception as exc:
            log.error("code_agent.tool_error", tool=call.tool_name, error=str(exc))
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=str(exc),
            )

    async def _read_file(self, call: ToolCall) -> ToolResult:
        path = Path(call.arguments["path"])
        if not path.exists():
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"File not found: {path}",
            )
        content = await asyncio.to_thread(path.read_text, encoding="utf-8")
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=content[:12000],
        )

    async def _write_file(self, call: ToolCall) -> ToolResult:
        path = Path(call.arguments["path"])
        if not _is_safe_write_path(path):
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=(
                    f"Write blocked by sandbox: '{path}' is outside"
                    f" allowed roots {_SAFE_WRITE_ROOTS}"
                ),
            )
        content = call.arguments["content"]
        # Atomic write
        import os
        import tempfile

        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", dir=path.parent, delete=False, suffix=".tmp", encoding="utf-8"
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        os.replace(tmp_path, path)
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=f"Written {len(content)} chars to {path}",
        )

    async def _run_subprocess(self, call: ToolCall, cmd: list[str]) -> ToolResult:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = stdout.decode("utf-8", errors="replace")
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=(proc.returncode == 0),
            result=output[:8000] if proc.returncode == 0 else None,
            error=output[:8000] if proc.returncode != 0 else None,
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
