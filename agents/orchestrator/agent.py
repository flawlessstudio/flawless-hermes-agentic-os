"""Orchestrator/Planner agent — task decomposition, routing, and aggregation."""

from __future__ import annotations

import json
from typing import Any

import structlog

from hermes_orchestrator.agent import BaseAgent
from hermes_orchestrator.schemas import AgentConfig, ToolCall, ToolResult

log = structlog.get_logger(__name__)

_AGENT_ROSTER = [
    {
        "role": "research",
        "description": "Web search, URL fetching, entity extraction, memory retrieval",
        "capabilities": ["web_search", "fetch_url", "extract_entities", "semantic_search"],
    },
    {
        "role": "code",
        "description": "Code generation, review, testing, linting, type checking",
        "capabilities": ["read_file", "write_file", "run_tests", "lint", "run_type_check"],
    },
    {
        "role": "ops",
        "description": "System health, CI/CD, monitoring, log tailing, Docker",
        "capabilities": ["health_check", "run_ci_check", "tail_api_logs", "ping_health_endpoint"],
    },
    {
        "role": "data",
        "description": "SQL analytics, CSV loading, ChromaDB queries, data summarization",
        "capabilities": ["execute_sql", "load_csv", "query_chromadb", "summarize_dataframe"],
    },
    {
        "role": "security",
        "description": "SAST scanning, secret detection, SBOM analysis, Dockerfile hardening",
        "capabilities": ["run_semgrep", "check_secrets_gitleaks", "analyze_sbom"],
    },
    {
        "role": "writer",
        "description": "Markdown docs, changelog generation, docstring extraction, templates",
        "capabilities": ["write_markdown", "generate_changelog", "extract_docstrings"],
    },
]


class OrchestratorAgent(BaseAgent):
    """Planner/orchestrator agent for task decomposition and multi-agent routing."""

    ALLOWED_TOOLS: frozenset[str] = frozenset(
        {
            "decompose_task",
            "route_to_agent",
            "aggregate_results",
            "human_checkpoint",
            "get_agent_roster",
        }
    )

    TOOL_SCHEMAS: list[dict[str, Any]] = [  # noqa: RUF012
        {
            "name": "decompose_task",
            "description": "Break a complex task into ordered sub-tasks with agent assignments.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "The high-level task to decompose."},
                    "context": {
                        "type": "string",
                        "description": "Optional additional context for decomposition.",
                    },
                },
                "required": ["task"],
            },
        },
        {
            "name": "route_to_agent",
            "description": "Route a specific sub-task to the appropriate specialist agent.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "agent_role": {
                        "type": "string",
                        "description": (
                            "Target agent role (research/code/ops/data/security/writer)."
                        ),
                    },
                    "task": {"type": "string", "description": "Task description for the agent."},
                    "priority": {
                        "type": "string",
                        "description": "Task priority: low/normal/high/critical.",
                        "default": "normal",
                    },
                },
                "required": ["agent_role", "task"],
            },
        },
        {
            "name": "aggregate_results",
            "description": "Aggregate multiple agent results into a unified output.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "List of result dicts from various agents.",
                    },
                    "aggregation_strategy": {
                        "type": "string",
                        "description": "Strategy: summary/merge/vote/sequential.",
                        "default": "summary",
                    },
                },
                "required": ["results"],
            },
        },
        {
            "name": "human_checkpoint",
            "description": "Pause execution and request human confirmation or input.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question or decision to present to the human.",
                    },
                    "context": {
                        "type": "string",
                        "description": "Background context to help the human decide.",
                    },
                },
                "required": ["question", "context"],
            },
        },
        {
            "name": "get_agent_roster",
            "description": "List all available agents with their roles and capabilities.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
    ]

    async def handle_tool(self, call: ToolCall) -> ToolResult:
        """Execute a verified tool call."""
        try:
            if call.tool_name == "decompose_task":
                return await self._decompose_task(call)
            if call.tool_name == "route_to_agent":
                return await self._route_to_agent(call)
            if call.tool_name == "aggregate_results":
                return await self._aggregate_results(call)
            if call.tool_name == "human_checkpoint":
                return await self._human_checkpoint(call)
            if call.tool_name == "get_agent_roster":
                return await self._get_agent_roster(call)
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Tool '{call.tool_name}' not implemented in OrchestratorAgent",
            )
        except Exception as exc:
            log.error("orchestrator_agent.tool_error", tool=call.tool_name, error=str(exc))
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=str(exc),
            )

    async def _decompose_task(self, call: ToolCall) -> ToolResult:
        task = call.arguments["task"]
        context = call.arguments.get("context", "")
        roster_roles = [a["role"] for a in _AGENT_ROSTER]
        plan = {
            "task": task,
            "context": context,
            "steps": [
                {
                    "step": 1,
                    "action": "Analyze requirements and identify sub-tasks",
                    "agent": "orchestrator",
                    "output": "Sub-task list with dependencies",
                },
                {
                    "step": 2,
                    "action": "Route each sub-task to the appropriate specialist agent",
                    "agent": f"one of: {roster_roles}",
                    "output": "Per-agent task assignments",
                },
                {
                    "step": 3,
                    "action": "Execute sub-tasks (parallel where possible)",
                    "agent": "multiple",
                    "output": "Individual agent results",
                },
                {
                    "step": 4,
                    "action": "Aggregate results and validate completeness",
                    "agent": "orchestrator",
                    "output": "Unified result",
                },
                {
                    "step": 5,
                    "action": "Apply critic pass — check for gaps, errors, or missing steps",
                    "agent": "orchestrator",
                    "output": "Final validated output or escalation",
                },
            ],
            "note": (
                "Adjust step count and agent assignments based on actual task complexity. "
                "Use human_checkpoint before irreversible actions."
            ),
        }
        log.info("orchestrator.decompose", task_len=len(task))
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=json.dumps(plan, indent=2),
        )

    async def _route_to_agent(self, call: ToolCall) -> ToolResult:
        agent_role = call.arguments["agent_role"]
        task = call.arguments["task"]
        priority = call.arguments.get("priority", "normal")
        valid_roles = {a["role"] for a in _AGENT_ROSTER}
        if agent_role not in valid_roles:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Unknown agent role '{agent_role}'. Valid: {sorted(valid_roles)}",
            )
        routing = {
            "status": "routed",
            "agent_role": agent_role,
            "task": task,
            "priority": priority,
            "message": (
                f"Task queued for {agent_role} agent at priority={priority}. "
                "In a live system this would publish to the AsyncMessageBus."
            ),
        }
        log.info("orchestrator.route", agent=agent_role, priority=priority)
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=json.dumps(routing, indent=2),
        )

    async def _aggregate_results(self, call: ToolCall) -> ToolResult:
        results = call.arguments["results"]
        strategy = call.arguments.get("aggregation_strategy", "summary")
        if not results:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error="No results to aggregate",
            )
        successes = [r for r in results if r.get("success", True)]
        failures = [r for r in results if not r.get("success", True)]
        aggregated = {
            "strategy": strategy,
            "total_results": len(results),
            "successful": len(successes),
            "failed": len(failures),
            "summary": f"Aggregated {len(results)} results using '{strategy}' strategy.",
            "results": results,
        }
        if strategy == "vote":
            aggregated["majority_outcome"] = (
                "success" if len(successes) > len(failures) else "failure"
            )
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=json.dumps(aggregated, indent=2),
        )

    async def _human_checkpoint(self, call: ToolCall) -> ToolResult:
        question = call.arguments["question"]
        context = call.arguments["context"]
        message = (
            "=== PAUSA HUMANA ===\n"
            f"Context: {context}\n\n"
            f"Question: {question}\n\n"
            "Please provide your answer or confirmation before the agent proceeds.\n"
            "=== END PAUSA HUMANA ==="
        )
        log.warning("orchestrator.human_checkpoint", question=question[:100])
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=message,
        )

    async def _get_agent_roster(self, call: ToolCall) -> ToolResult:
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=json.dumps(_AGENT_ROSTER, indent=2),
        )


def make_orchestrator_agent() -> OrchestratorAgent:
    """Factory: create an OrchestratorAgent with default configuration."""
    config = AgentConfig(
        agent_id="orchestrator",
        model="claude-sonnet-4-6",
        allowed_tools=OrchestratorAgent.ALLOWED_TOOLS,
        system_prompt=(
            "You are the Hermes Orchestrator — a planner/executor/critic agent. "
            "Your role is task decomposition, agent routing, and result aggregation. "
            "Pattern: (1) Plan — decompose the task into clear steps. "
            "(2) Execute — route each step to the right specialist agent. "
            "(3) Critique — review outputs for gaps, errors, and completeness. "
            "Always use human_checkpoint before irreversible actions. "
            "Prefer parallel execution where sub-tasks are independent. "
            "Be explicit about assumptions and flag blockers immediately."
        ),
    )
    return OrchestratorAgent(config=config)
