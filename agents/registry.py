"""Central Agent Registry — single source of truth for all Hermes agents.

Usage::

    from agents.registry import make_agent, AGENT_CATALOG

    agent = make_agent("research")
    result = await agent.run("What is the latest news on AI?")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from hermes_orchestrator.agent import BaseAgent

from agents.code.agent import CodeAgent, make_code_agent
from agents.data.agent import DataAgent, make_data_agent
from agents.ops.agent import OpsAgent, make_ops_agent
from agents.orchestrator.agent import OrchestratorAgent, make_orchestrator_agent
from agents.research.agent import ResearchAgent, make_research_agent
from agents.security.agent import SecurityAgent, make_security_agent
from agents.writer.agent import WriterAgent, make_writer_agent

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Agent catalog — role metadata for routing and discovery
# ---------------------------------------------------------------------------
AGENT_CATALOG: dict[str, dict[str, Any]] = {
    "orchestrator": {
        "role": "orchestrator",
        "description": (
            "Top-level planner and router. Decomposes goals, routes to specialists, "
            "validates results, and aggregates outputs. Faces the user directly."
        ),
        "allowed_tools": list(OrchestratorAgent.ALLOWED_TOOLS),
        "model": "claude-sonnet-4-6",
        "class": OrchestratorAgent,
        "factory": make_orchestrator_agent,
    },
    "research": {
        "role": "research",
        "description": (
            "Information research and synthesis. Web search, URL fetching, entity extraction, "
            "semantic search, and knowledge retrieval with citation."
        ),
        "allowed_tools": list(ResearchAgent.ALLOWED_TOOLS),
        "model": "claude-sonnet-4-6",
        "class": ResearchAgent,
        "factory": make_research_agent,
    },
    "code": {
        "role": "code",
        "description": (
            "Software engineering: code generation, review, testing, refactoring, "
            "type checking, dependency management, and complexity analysis."
        ),
        "allowed_tools": list(CodeAgent.ALLOWED_TOOLS),
        "model": "claude-sonnet-4-6",
        "class": CodeAgent,
        "factory": make_code_agent,
    },
    "ops": {
        "role": "ops",
        "description": (
            "DevOps and system operations: health checks, log tailing, CI/CD, "
            "disk usage, health endpoint monitoring, and Docker Compose inspection."
        ),
        "allowed_tools": list(OpsAgent.ALLOWED_TOOLS),
        "model": "claude-sonnet-4-6",
        "class": OpsAgent,
        "factory": make_ops_agent,
    },
    "data": {
        "role": "data",
        "description": (
            "Data engineering and analytics: DuckDB SQL, CSV loading, schema description, "
            "ChromaDB vector queries, and dataframe summarisation."
        ),
        "allowed_tools": list(DataAgent.ALLOWED_TOOLS),
        "model": "claude-sonnet-4-6",
        "class": DataAgent,
        "factory": make_data_agent,
    },
    "security": {
        "role": "security",
        "description": (
            "Application security: SAST via Semgrep, OSV dependency scanning, "
            "secret detection via Gitleaks, Dockerfile analysis, and SBOM generation."
        ),
        "allowed_tools": list(SecurityAgent.ALLOWED_TOOLS),
        "model": "claude-sonnet-4-6",
        "class": SecurityAgent,
        "factory": make_security_agent,
    },
    "writer": {
        "role": "writer",
        "description": (
            "Technical writing: markdown documentation, changelog generation, "
            "docstring extraction, template rendering, and API reference docs."
        ),
        "allowed_tools": list(WriterAgent.ALLOWED_TOOLS),
        "model": "claude-sonnet-4-6",
        "class": WriterAgent,
        "factory": make_writer_agent,
    },
}

_FACTORIES = {
    "orchestrator": make_orchestrator_agent,
    "research": make_research_agent,
    "code": make_code_agent,
    "ops": make_ops_agent,
    "data": make_data_agent,
    "security": make_security_agent,
    "writer": make_writer_agent,
}


def make_agent(role: str) -> BaseAgent:
    """Factory function — create an agent by role name.

    Parameters
    ----------
    role:
        One of: orchestrator, research, code, ops, data, security, writer.

    Returns
    -------
    BaseAgent
        A fully configured agent instance ready to call ``.run()``.

    Raises
    ------
    ValueError
        If the role is not registered in the catalog.
    """
    if role not in _FACTORIES:
        available = ", ".join(sorted(_FACTORIES))
        raise ValueError(f"Unknown agent role: {role!r}. Available: {available}")
    log.info("registry.make_agent", role=role)
    return _FACTORIES[role]()


__all__ = [
    "AGENT_CATALOG",
    "CodeAgent",
    "DataAgent",
    "OpsAgent",
    "OrchestratorAgent",
    "ResearchAgent",
    "SecurityAgent",
    "WriterAgent",
    "make_agent",
    "make_code_agent",
    "make_data_agent",
    "make_ops_agent",
    "make_orchestrator_agent",
    "make_research_agent",
    "make_security_agent",
    "make_writer_agent",
]
