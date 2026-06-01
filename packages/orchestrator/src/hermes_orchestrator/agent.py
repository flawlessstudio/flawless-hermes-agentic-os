"""BaseAgent — Claude-backed agent with tool whitelist and sandbox enforcement.

Every concrete agent subclasses :class:`BaseAgent`, declares its
``ALLOWED_TOOLS`` frozenset, and implements the tool handlers it needs.
The base class handles the conversation loop, sandbox gate, and structured
logging.

Usage::

    class ResearchAgent(BaseAgent):
        ALLOWED_TOOLS: frozenset[str] = frozenset({"search_web", "read_url"})

        async def handle_tool(self, call: ToolCall) -> ToolResult:
            if call.tool_name == "search_web":
                ...

    config = AgentConfig(agent_id="research_1", system_prompt="You are a researcher.")
    agent = ResearchAgent(config=config)
    result = await agent.run("What is the latest news on AI?")
"""

from __future__ import annotations

import abc
from typing import Any

import structlog

from hermes_orchestrator.bus import AsyncMessageBus
from hermes_orchestrator.sandbox import Sandbox, SandboxViolation
from hermes_orchestrator.schemas import AgentConfig, AgentMessage, ToolCall, ToolResult

log = structlog.get_logger(__name__)

try:
    import anthropic

    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


class BaseAgent(abc.ABC):
    """Abstract base class for all Hermes agents.

    Subclasses must:
    1. Declare :attr:`ALLOWED_TOOLS` — a frozenset of permitted tool names.
    2. Implement :meth:`handle_tool` — called when Claude requests a tool.
    3. (Optional) Override :attr:`TOOL_SCHEMAS` with Anthropic tool definitions.

    Parameters
    ----------
    config:
        :class:`AgentConfig` containing model settings and the allowed tools.
        If ``config.allowed_tools`` is non-empty it *overrides* the class-level
        ``ALLOWED_TOOLS``.
    """

    #: Class-level tool whitelist.  Override in subclasses.
    ALLOWED_TOOLS: frozenset[str] = frozenset()

    #: Anthropic tool schema definitions.  Override in subclasses.
    TOOL_SCHEMAS: list[dict[str, Any]] = []  # noqa: RUF012

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        # Config-level allowed_tools overrides class-level declaration.
        effective_tools = config.allowed_tools if config.allowed_tools else self.ALLOWED_TOOLS
        self._sandbox = Sandbox(
            agent_id=config.agent_id,
            allowed_tools=effective_tools,
        )
        self._conversation: list[dict[str, Any]] = []
        self._log = log.bind(agent_id=config.agent_id, model=config.model)

        if _ANTHROPIC_AVAILABLE:
            self._client = anthropic.AsyncAnthropic()
        else:
            self._client = None

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def run(self, user_message: str) -> str:
        """Run a single user turn through the agentic loop.

        Sends *user_message* to Claude and handles any tool calls until
        Claude produces a final text response.

        Parameters
        ----------
        user_message:
            The human-turn message to send.

        Returns
        -------
        str
            The final text response from the model.

        Raises
        ------
        RuntimeError
            If the ``anthropic`` package is not installed.
        """
        if not _ANTHROPIC_AVAILABLE or self._client is None:
            raise RuntimeError("anthropic package is required. Install with: pip install anthropic")

        self._conversation.append({"role": "user", "content": user_message})
        self._log.info("agent.turn_start", message_len=len(user_message))

        while True:
            response = await self._client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=self.config.system_prompt,
                messages=self._conversation,
                tools=self.TOOL_SCHEMAS if self.TOOL_SCHEMAS else anthropic.NOT_GIVEN,
            )
            self._log.debug(
                "agent.api_response",
                stop_reason=response.stop_reason,
                content_blocks=len(response.content),
            )

            # Collect text output and tool uses from this response.
            text_blocks: list[str] = []
            tool_uses: list[Any] = []

            for block in response.content:
                if block.type == "text":
                    text_blocks.append(block.text)
                elif block.type == "tool_use":
                    tool_uses.append(block)

            # Append assistant message to conversation history.
            self._conversation.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn" or not tool_uses:
                final_text = "\n".join(text_blocks)
                self._log.info("agent.turn_complete", response_len=len(final_text))
                return final_text

            # Process tool calls.
            tool_results: list[dict[str, Any]] = []
            for tool_use in tool_uses:
                tool_name = tool_use.name
                try:
                    # GATE: sandbox enforces the whitelist.
                    self._sandbox.check(tool_name)
                    call = ToolCall(
                        tool_name=tool_name,
                        arguments=dict(tool_use.input),
                        call_id=tool_use.id,
                    )
                    result = await self.handle_tool(call)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": str(result.result)
                            if result.success
                            else f"Error: {result.error}",
                        }
                    )
                except SandboxViolation as exc:
                    self._log.error("agent.sandbox_violation", tool_name=tool_name, error=str(exc))
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": f"SandboxViolation: {exc}",
                            "is_error": True,
                        }
                    )

            self._conversation.append({"role": "user", "content": tool_results})

    def reset(self) -> None:
        """Clear conversation history, starting a fresh session."""
        self._conversation.clear()
        self._log.debug("agent.reset")

    # ------------------------------------------------------------------ #
    # Abstract methods                                                     #
    # ------------------------------------------------------------------ #

    @abc.abstractmethod
    async def handle_tool(self, call: ToolCall) -> ToolResult:
        """Execute a tool call and return the result.

        This method is only called for tools that passed the sandbox gate.

        Parameters
        ----------
        call:
            The validated tool invocation.

        Returns
        -------
        ToolResult
            Success or failure result of the tool execution.
        """
        ...

    async def handle_message(self, message: AgentMessage) -> None:  # noqa: B027
        """Handle an incoming :class:`AgentMessage` from the bus.

        Default implementation is a no-op.  Override in subclasses to
        react to messages from other agents.

        Parameters
        ----------
        message:
            The incoming message.
        """

    @classmethod
    def default_config(cls) -> AgentConfig:
        """Return the default :class:`AgentConfig` for this agent type.

        Override in subclasses to provide pre-configured defaults.
        """
        return AgentConfig(agent_id=cls.__name__.lower())

    async def send_message(
        self,
        recipient_id: str,
        topic: str,
        payload: dict[str, Any] | None = None,
        bus: AsyncMessageBus | None = None,
    ) -> None:
        """Send a message to another agent via the bus.

        Parameters
        ----------
        recipient_id:
            Target agent ID.
        topic:
            Message topic string.
        payload:
            Optional message payload.
        bus:
            :class:`AsyncMessageBus` instance to publish on.  If ``None``,
            the message is silently dropped (useful in tests).
        """
        if bus is None:
            self._log.debug("agent.send_message.no_bus", recipient_id=recipient_id, topic=topic)
            return
        msg = AgentMessage(
            sender_id=self.config.agent_id,
            recipient_id=recipient_id,
            topic=topic,
            payload=payload or {},
        )
        await bus.publish(msg)

    # ------------------------------------------------------------------ #
    # Dunder helpers                                                       #
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(agent_id={self.config.agent_id!r}, model={self.config.model!r})"
        )
