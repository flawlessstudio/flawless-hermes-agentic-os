"""Writer agent — documentation, changelogs, docstrings, and technical reports."""

from __future__ import annotations

import ast
import json
import string
import subprocess
from pathlib import Path
from typing import Any

import structlog

from hermes_orchestrator.agent import BaseAgent
from hermes_orchestrator.schemas import AgentConfig, ToolCall, ToolResult

log = structlog.get_logger(__name__)

_SAFE_WRITE_ROOTS: frozenset[str] = frozenset({"docs", "changelogs", "reports"})


def _is_safe_write_path(path: Path) -> bool:
    try:
        resolved = path.resolve()
        parts = resolved.relative_to(Path.cwd()).parts
        return bool(parts) and parts[0] in _SAFE_WRITE_ROOTS
    except ValueError:
        return False


class WriterAgent(BaseAgent):
    """Technical writer agent: markdown docs, changelogs, docstrings, reports.

    Write posture: output restricted to docs/, changelogs/, reports/.
    Source code is read-only. Never modifies .py/.ts files.
    """

    ALLOWED_TOOLS: frozenset[str] = frozenset(
        {
            "read_file",
            "write_markdown",
            "generate_changelog",
            "extract_docstrings",
            "render_template",
        }
    )

    TOOL_SCHEMAS: list[dict[str, Any]] = [  # noqa: RUF012
        {
            "name": "read_file",
            "description": (
                "Read any text file in the repository (source, config, existing docs). "
                "Use to understand the code before documenting it."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative or absolute path."},
                    "max_bytes": {
                        "type": "integer",
                        "default": 32768,
                        "description": "Truncate at this byte count to avoid overload.",
                    },
                },
                "required": ["path"],
            },
        },
        {
            "name": "write_markdown",
            "description": (
                "Write a markdown document to docs/, changelogs/, or reports/. "
                "Creates parent directories automatically. Atomic write (temp → rename). "
                "Fails if the destination path leaves the allowed roots."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Destination path (must be under docs/, changelogs/, or reports/)."
                        ),
                    },
                    "content": {"type": "string", "description": "Full markdown content."},
                },
                "required": ["path", "content"],
            },
        },
        {
            "name": "generate_changelog",
            "description": (
                "Generate a Keep-a-Changelog formatted entry from git history. "
                "Groups commits by type: Added, Changed, Fixed, Security. "
                "Returns raw markdown ready to prepend to CHANGELOG.md."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "since": {
                        "type": "string",
                        "description": "Git ref (tag, commit, branch) to start from.",
                        "default": "HEAD~20",
                    },
                    "version": {
                        "type": "string",
                        "description": "Version string for the new section (e.g. '1.2.0').",
                        "default": "Unreleased",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "extract_docstrings",
            "description": (
                "Parse a Python file with ast and extract all module, class, and function "
                "docstrings. Returns a structured list of {type, name, docstring}. "
                "Use to audit documentation coverage or generate API reference."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to a .py file."},
                },
                "required": ["path"],
            },
        },
        {
            "name": "render_template",
            "description": (
                "Render a document using Python string.Template substitution. "
                "Provide the template string and a variables dict. "
                "Use for structured reports, release notes, or onboarding docs."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "template": {
                        "type": "string",
                        "description": (
                            "Template string with $variable or ${variable} placeholders."
                        ),
                    },
                    "variables": {
                        "type": "object",
                        "description": "Substitution dict.",
                    },
                },
                "required": ["template", "variables"],
            },
        },
    ]

    async def handle_tool(self, call: ToolCall) -> ToolResult:
        try:
            if call.tool_name == "read_file":
                return self._read_file(call)
            if call.tool_name == "write_markdown":
                return self._write_markdown(call)
            if call.tool_name == "generate_changelog":
                return self._generate_changelog(call)
            if call.tool_name == "extract_docstrings":
                return self._extract_docstrings(call)
            if call.tool_name == "render_template":
                return self._render_template(call)
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Unknown tool: {call.tool_name}",
            )
        except Exception as exc:
            log.error("writer_agent.tool_error", tool=call.tool_name, error=str(exc))
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=str(exc),
            )

    def _read_file(self, call: ToolCall) -> ToolResult:
        path = Path(call.arguments["path"])
        max_bytes = int(call.arguments.get("max_bytes", 32768))
        if not path.exists():
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"File not found: {path}",
            )
        content = path.read_bytes()[:max_bytes].decode("utf-8", errors="replace")
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=content,
        )

    def _write_markdown(self, call: ToolCall) -> ToolResult:
        path = Path(call.arguments["path"])
        if not _is_safe_write_path(path):
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=(
                    f"Write blocked: '{path}' is outside allowed roots "
                    f"({', '.join(sorted(_SAFE_WRITE_ROOTS))}). "
                    "WriterAgent is read-only on source code."
                ),
            )
        content = call.arguments["content"]
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp.write_text(content, encoding="utf-8")
            tmp.replace(path)
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=True,
                result=f"Written {len(content)} bytes to {path}",
            )
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=str(exc),
            )

    def _generate_changelog(self, call: ToolCall) -> ToolResult:
        since = call.arguments.get("since", "HEAD~20")
        version = call.arguments.get("version", "Unreleased")
        try:
            result = subprocess.run(  # noqa: S603
                [  # noqa: S607
                    "git",
                    "log",
                    f"{since}..HEAD",
                    "--oneline",
                    "--no-merges",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            lines = result.stdout.strip().splitlines()
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=str(exc),
            )

        buckets: dict[str, list[str]] = {
            "Added": [],
            "Changed": [],
            "Fixed": [],
            "Security": [],
            "Other": [],
        }
        for line in lines:
            msg = line[8:].strip() if len(line) > 8 else line
            lower = msg.lower()
            if any(k in lower for k in ("add", "new", "feat", "implement")):
                buckets["Added"].append(msg)
            elif any(k in lower for k in ("fix", "bug", "patch", "resolve")):
                buckets["Fixed"].append(msg)
            elif any(k in lower for k in ("security", "cve", "secret", "vuln")):
                buckets["Security"].append(msg)
            elif any(k in lower for k in ("update", "refactor", "change", "improve", "upgrade")):
                buckets["Changed"].append(msg)
            else:
                buckets["Other"].append(msg)

        from datetime import UTC, datetime

        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        md_lines = [f"## [{version}] — {date_str}", ""]
        for section, items in buckets.items():
            if items:
                md_lines.append(f"### {section}")
                md_lines.extend(f"- {item}" for item in items)
                md_lines.append("")
        changelog_md = "\n".join(md_lines)
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=changelog_md,
        )

    def _extract_docstrings(self, call: ToolCall) -> ToolResult:
        path = Path(call.arguments["path"])
        if not path.exists():
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"File not found: {path}",
            )
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Syntax error in {path}: {exc}",
            )

        entries: list[dict[str, Any]] = []
        for node in ast.walk(tree):
            doc = ast.get_docstring(node)
            if doc is None:
                continue
            if isinstance(node, ast.Module):
                entries.append({"type": "module", "name": str(path), "docstring": doc})
            elif isinstance(node, ast.ClassDef):
                entries.append({"type": "class", "name": node.name, "docstring": doc})
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                entries.append({"type": "function", "name": node.name, "docstring": doc})

        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=json.dumps(entries, indent=2),
        )

    def _render_template(self, call: ToolCall) -> ToolResult:
        template_str = call.arguments["template"]
        variables = call.arguments.get("variables", {})
        try:
            rendered = string.Template(template_str).substitute(variables)
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=True,
                result=rendered,
            )
        except (KeyError, ValueError) as exc:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Template substitution error: {exc}",
            )


def make_writer_agent() -> WriterAgent:
    """Factory: create a WriterAgent with production configuration."""
    config = AgentConfig(
        agent_id="writer",
        model="claude-sonnet-4-6",
        allowed_tools=WriterAgent.ALLOWED_TOOLS,
        system_prompt=(
            "You are a technical writer for the Hermes Agent OS.\n\n"
            "YOUR MANDATE:\n"
            "- Produce clear, accurate, and maintainable documentation.\n"
            "- Always read the source before writing about it — never hallucinate APIs.\n"
            "- Follow Keep a Changelog format (keepachangelog.com) for all changelogs.\n"
            "- Use Google Developer Documentation Style Guide conventions.\n"
            "- Write for the reader who arrives cold — no assumed context.\n\n"
            "WRITE POSTURE:\n"
            "- Output is restricted to docs/, changelogs/, reports/.\n"
            "- NEVER modify .py, .ts, .json, .toml, or any source file.\n"
            "- Docstring extraction is read-only; edits go to the CodeAgent.\n\n"
            "WORKFLOW:\n"
            "1. read_file the relevant source(s) to understand the API.\n"
            "2. extract_docstrings for Python modules to audit coverage.\n"
            "3. Draft content and write_markdown to the appropriate path.\n"
            "4. For release notes: generate_changelog, review, write_markdown to changelogs/.\n"
            "5. For templated reports: render_template then write_markdown.\n\n"
            "STYLE: Be precise, scannable (headers + bullet points), and concise. "
            "No filler phrases. No apologies. Cite the source file and line when referencing code."
        ),
    )
    return WriterAgent(config=config)
