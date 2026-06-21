"""Security agent — SAST, dependency scanning, secret detection, container analysis."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog

from hermes_orchestrator.agent import BaseAgent
from hermes_orchestrator.schemas import AgentConfig, ToolCall, ToolResult

log = structlog.get_logger(__name__)


class SecurityAgent(BaseAgent):
    """AppSec agent: SAST, OSV dependency scan, secret detection, SBOM, Dockerfile analysis.

    All operations are READ-ONLY and REPORT-ONLY. The agent never modifies files.
    Destructive remediation requires PAUSA HUMANA via the Orchestrator.
    """

    ALLOWED_TOOLS: frozenset[str] = frozenset(
        {
            "run_semgrep",
            "run_osv_scan",
            "check_secrets_gitleaks",
            "analyze_sbom",
            "scan_dockerfile",
        }
    )

    TOOL_SCHEMAS: list[dict[str, Any]] = [  # noqa: RUF012
        {
            "name": "run_semgrep",
            "description": (
                "Run Semgrep SAST scan on the project. Detects security vulnerabilities, "
                "code quality issues, and OWASP Top 10 patterns. "
                "Returns findings with severity, file, line, and remediation guidance."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "default": ".",
                        "description": "Directory to scan.",
                    },
                    "config": {
                        "type": "string",
                        "default": "auto",
                        "description": "Semgrep config (auto, p/python, p/security, etc.).",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "run_osv_scan",
            "description": (
                "Run OSV Scanner to detect known CVEs in Python and Node dependencies. "
                "Cross-references against the OSV vulnerability database. "
                "Returns CVE ids, severity, affected versions, and fix status."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "default": ".", "description": "Repo root."},
                },
                "required": [],
            },
        },
        {
            "name": "check_secrets_gitleaks",
            "description": (
                "Detect hardcoded secrets, tokens, and credentials in git history and "
                "working tree using Gitleaks. Reports file, line, secret type, and entropy. "
                "Zero-tolerance: any finding is CRITICAL severity."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "default": ".", "description": "Repo root."},
                    "staged_only": {
                        "type": "boolean",
                        "default": False,
                        "description": "Scan only staged changes.",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "analyze_sbom",
            "description": (
                "Generate a Software Bill of Materials from uv pip freeze and pnpm list. "
                "Lists all direct and transitive dependencies with versions. "
                "Use before releases or security audits."
            ),
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "scan_dockerfile",
            "description": (
                "Statically analyse the project Dockerfile for security best practices: "
                "non-root user, no secrets in ENV/ARG, pinned base images, "
                "HEALTHCHECK presence, minimal attack surface. "
                "Returns pass/fail per check with remediation advice."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "default": "Dockerfile",
                        "description": "Path to Dockerfile.",
                    },
                },
                "required": [],
            },
        },
    ]

    async def handle_tool(self, call: ToolCall) -> ToolResult:
        try:
            if call.tool_name == "run_semgrep":
                return await self._run_semgrep(call)
            if call.tool_name == "run_osv_scan":
                return await self._run_osv_scan(call)
            if call.tool_name == "check_secrets_gitleaks":
                return await self._check_secrets(call)
            if call.tool_name == "analyze_sbom":
                return await self._analyze_sbom(call)
            if call.tool_name == "scan_dockerfile":
                return await self._scan_dockerfile(call)
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Unknown tool: {call.tool_name}",
            )
        except Exception as exc:
            log.error("security_agent.tool_error", tool=call.tool_name, error=str(exc))
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=str(exc),
            )

    async def _run_subprocess(
        self, call: ToolCall, cmd: list[str], timeout: int = 120
    ) -> ToolResult:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            output = stdout.decode("utf-8", errors="replace")
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=(proc.returncode == 0),
                result=output[:10000] if proc.returncode == 0 else None,
                error=output[:10000] if proc.returncode != 0 else None,
            )
        except FileNotFoundError as exc:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Tool not found: {exc}. Install it and retry.",
            )

    async def _run_semgrep(self, call: ToolCall) -> ToolResult:
        path = call.arguments.get("path", ".")
        config = call.arguments.get("config", "auto")
        return await self._run_subprocess(
            call,
            ["semgrep", "scan", f"--config={config}", "--json", "--quiet", path],
        )

    async def _run_osv_scan(self, call: ToolCall) -> ToolResult:
        path = call.arguments.get("path", ".")
        # Use osv-scanner.toml if present
        from pathlib import Path

        toml_path = Path(path) / "osv-scanner.toml"
        cmd = ["osv-scanner", "--recursive", "--format=json"]
        if toml_path.exists():
            cmd += [f"--config={toml_path}"]
        cmd.append(path)
        return await self._run_subprocess(call, cmd)

    async def _check_secrets(self, call: ToolCall) -> ToolResult:
        path = call.arguments.get("path", ".")
        staged = call.arguments.get("staged_only", False)
        cmd = ["gitleaks", "detect", "--source", path, "--no-banner", "--report-format", "json"]
        if staged:
            cmd += ["--staged"]
        result = await self._run_subprocess(call, cmd)
        # gitleaks exits 1 if secrets found — treat as success (findings reported)
        if result.error and "leaks found" in (result.error or "").lower():
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=True,
                result=result.error,
            )
        return result

    async def _analyze_sbom(self, call: ToolCall) -> ToolResult:
        py_proc = await asyncio.create_subprocess_exec(
            "uv",
            "pip",
            "freeze",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        py_out, _ = await py_proc.communicate()

        node_proc = await asyncio.create_subprocess_exec(
            "pnpm",
            "list",
            "--json",
            "--depth=0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        node_out, _ = await node_proc.communicate()

        sbom = {
            "python_deps": py_out.decode("utf-8", errors="replace").splitlines(),
            "node_deps_json": node_out.decode("utf-8", errors="replace")[:5000],
        }
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=json.dumps(sbom, indent=2),
        )

    async def _scan_dockerfile(self, call: ToolCall) -> ToolResult:
        from pathlib import Path

        path = Path(call.arguments.get("path", "Dockerfile"))
        if not path.exists():
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Dockerfile not found: {path}",
            )
        content = path.read_text(encoding="utf-8")
        checks: list[dict[str, Any]] = []

        def chk(name: str, passed: bool, detail: str) -> None:
            checks.append({"check": name, "passed": passed, "detail": detail})

        chk(
            "non-root user",
            "USER " in content and "USER root" not in content.split("USER ")[-1].split("\n")[0],
            "Dockerfile should declare a non-root USER before CMD/ENTRYPOINT.",
        )
        chk(
            "no secrets in ENV/ARG",
            not any(kw in content.upper() for kw in ["PASSWORD=", "SECRET=", "API_KEY=", "TOKEN="]),
            "Secrets must never be set via ENV or ARG — use runtime env injection.",
        )
        chk(
            "HEALTHCHECK present",
            "HEALTHCHECK" in content,
            "Add HEALTHCHECK for container orchestration liveness probes.",
        )
        chk(
            "pinned base image",
            any(
                f"FROM {img}:" in content and "@sha256:" not in content
                for img in ["python", "node", "ubuntu", "debian", "alpine"]
            )
            is False,
            "Pin base images to digest (@sha256:...) for reproducibility.",
        )
        chk(
            "multi-stage build",
            content.count("FROM ") > 1,
            "Multi-stage builds reduce final image attack surface.",
        )

        passed = sum(1 for c in checks if c["passed"])
        total = len(checks)
        summary = f"{passed}/{total} checks passed."
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=passed == total,
            result=json.dumps({"summary": summary, "checks": checks}, indent=2),
        )


def make_security_agent() -> SecurityAgent:
    """Factory: create a SecurityAgent with production configuration."""
    config = AgentConfig(
        agent_id="security",
        model="claude-sonnet-4-6",
        allowed_tools=SecurityAgent.ALLOWED_TOOLS,
        system_prompt=(
            "You are an application security (AppSec) agent for the Hermes Agent OS.\n\n"
            "YOUR MANDATE:\n"
            "- OWASP Top 10 awareness: injection, broken auth, sensitive data exposure, "
            "XXE, broken access control, security misconfiguration, XSS, insecure "
            "deserialisation, known vulns, insufficient logging.\n"
            "- Zero tolerance for secrets: any hardcoded credential is CRITICAL regardless "
            "of context or apparent sensitivity.\n"
            "- Read-only posture: you report findings, you NEVER modify files or apply "
            "fixes. Remediation goes through the CodeAgent with human approval.\n"
            "- Complete coverage: run all available scanners before concluding. "
            "A partial scan is not a clean scan.\n\n"
            "WORKFLOW:\n"
            "1. Run check_secrets_gitleaks first — a secret leak supersedes all else.\n"
            "2. Run run_osv_scan to surface known CVEs in dependencies.\n"
            "3. Run run_semgrep for SAST findings.\n"
            "4. Run scan_dockerfile if a Dockerfile is present.\n"
            "5. Run analyze_sbom to produce an inventory for the release.\n"
            "6. Synthesise findings by severity: CRITICAL → HIGH → MEDIUM → LOW.\n\n"
            "REPORT FORMAT:\n"
            "Severity | Finding | File:Line | OWASP Category | Remediation\n"
            "Never suppress or downgrade a finding. If in doubt, escalate."
        ),
    )
    return SecurityAgent(config=config)
