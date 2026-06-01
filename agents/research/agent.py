"""Research agent — web search, summarization, and knowledge retrieval."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import structlog

from hermes_orchestrator.agent import BaseAgent
from hermes_orchestrator.schemas import AgentConfig, ToolCall, ToolResult

log = structlog.get_logger(__name__)


class ResearchAgent(BaseAgent):
    """
    Specialized agent for information research and synthesis.

    Allowed tools: web_search, fetch_url, read_file, summarize, store_memory, recall_memory
    """

    ALLOWED_TOOLS: frozenset[str] = frozenset(
        {
            "web_search",
            "fetch_url",
            "read_file",
            "summarize",
            "store_memory",
            "recall_memory",
        }
    )

    TOOL_SCHEMAS: list[dict[str, Any]] = [  # noqa: RUF012
        {
            "name": "read_file",
            "description": "Read the contents of a local file.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative file path."}
                },
                "required": ["path"],
            },
        },
        {
            "name": "web_search",
            "description": "Search the web (requires EXA_API_KEY in env).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."},
                    "num_results": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
        {
            "name": "store_memory",
            "description": "Store a key-value fact in the agent's memory file.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["key", "value"],
            },
        },
        {
            "name": "recall_memory",
            "description": "Recall a previously stored memory by key.",
            "input_schema": {
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"],
            },
        },
    ]

    _MEMORY_PATH = Path(".hermes_research_memory.json")

    async def handle_tool(self, call: ToolCall) -> ToolResult:
        """Execute a verified tool call."""
        try:
            if call.tool_name == "read_file":
                return await self._read_file(call)
            if call.tool_name == "web_search":
                return await self._web_search(call)
            if call.tool_name == "store_memory":
                return await self._store_memory(call)
            if call.tool_name == "recall_memory":
                return await self._recall_memory(call)
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Tool '{call.tool_name}' not implemented in ResearchAgent",
            )
        except Exception as exc:
            log.error("research_agent.tool_error", tool=call.tool_name, error=str(exc))
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
            result=content[:8000],  # cap to 8k chars
        )

    async def _web_search(self, call: ToolCall) -> ToolResult:
        """Web search — requires EXA_API_KEY. Returns a stub if unavailable."""
        import os

        query = call.arguments["query"]
        api_key = os.environ.get("EXA_API_KEY")
        if not api_key:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error="EXA_API_KEY not set — PAUSA HUMANA: add key to .env to enable web search",
            )
        # Real Exa search via httpx
        try:
            import httpx

            num = int(call.arguments.get("num_results", 5))
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://api.exa.ai/search",
                    headers={"x-api-key": api_key, "Content-Type": "application/json"},
                    json={
                        "query": query,
                        "numResults": num,
                        "contents": {"text": {"maxCharacters": 500}},
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            results = [
                f"[{r.get('title', 'No title')}]({r.get('url', '')})\n{r.get('text', '')}"
                for r in data.get("results", [])
            ]
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=True,
                result="\n\n".join(results) or "No results found.",
            )
        except Exception as exc:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Search failed: {exc}",
            )

    async def _store_memory(self, call: ToolCall) -> ToolResult:
        key = call.arguments["key"]
        value = call.arguments["value"]
        mem: dict[str, str] = {}
        if self._MEMORY_PATH.exists():
            mem = json.loads(self._MEMORY_PATH.read_text())
        mem[key] = value
        self._MEMORY_PATH.write_text(json.dumps(mem, indent=2))
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=f"Stored: {key}",
        )

    async def _recall_memory(self, call: ToolCall) -> ToolResult:
        key = call.arguments["key"]
        if not self._MEMORY_PATH.exists():
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error="Memory store is empty",
            )
        mem: dict[str, str] = json.loads(self._MEMORY_PATH.read_text())
        if key not in mem:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Key not found: {key}",
            )
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=mem[key],
        )


def make_research_agent() -> ResearchAgent:
    """Factory: create a ResearchAgent with default configuration."""
    config = AgentConfig(
        agent_id="research",
        model="claude-sonnet-4-6",
        allowed_tools=ResearchAgent.ALLOWED_TOOLS,
        system_prompt=(
            "You are a research agent for the Hermes Agent OS. "
            "Your role is to find, synthesize, and summarize information accurately. "
            "Always cite sources. Flag uncertainty. Do not hallucinate facts. "
            "Store important findings in memory for later retrieval."
        ),
    )
    return ResearchAgent(config=config)
