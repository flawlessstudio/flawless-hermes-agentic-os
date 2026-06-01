"""Research agent — web search, summarization, and knowledge retrieval."""
from __future__ import annotations

from hermes_orchestrator.agent import BaseAgent
from hermes_orchestrator.schemas import AgentConfig, ToolCall, ToolResult


class ResearchAgent(BaseAgent):
    """
    Specialized agent for information research and synthesis.

    Allowed tools: web_search, fetch_url, read_file, summarize, store_memory, recall_memory
    """

    ALLOWED_TOOLS: frozenset[str] = frozenset({
        "web_search",
        "fetch_url",
        "read_file",
        "summarize",
        "store_memory",
        "recall_memory",
    })

    async def handle_tool(self, call: ToolCall) -> ToolResult:
        """Execute a verified tool call. Tools are wired via MCP in F4."""
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=False,
            error=f"Tool '{call.tool_name}' not yet wired to MCP backend",
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
