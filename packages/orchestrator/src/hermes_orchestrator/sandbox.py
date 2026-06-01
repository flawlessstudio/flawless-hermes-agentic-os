"""Sandbox — tool whitelist enforcement gate for agents.

Every agent declares an ``ALLOWED_TOOLS`` frozenset.  Any attempt to call a
tool whose name is not in that set raises :class:`SandboxViolation` — the
call is rejected before it ever reaches the Anthropic API.

This module is intentionally simple: security comes from the *absence* of
complexity, not from clever logic.

Usage::

    sandbox = Sandbox(allowed_tools=frozenset({"read_file", "search_web"}))
    sandbox.check("read_file")   # OK
    sandbox.check("delete_file") # raises SandboxViolation
"""

from __future__ import annotations

import structlog

from hermes_orchestrator.schemas import ToolCall

log = structlog.get_logger(__name__)


class SandboxViolation(Exception):
    """Raised when an agent attempts to call a tool not in its whitelist.

    Attributes
    ----------
    agent_id:
        ID of the agent that attempted the violation.
    tool_name:
        Name of the tool that was denied.
    allowed_tools:
        The set of tools the agent is permitted to use.
    """

    def __init__(
        self,
        agent_id: str,
        tool_name: str,
        allowed_tools: frozenset[str],
    ) -> None:
        self.agent_id = agent_id
        self.tool_name = tool_name
        self.allowed_tools = allowed_tools
        super().__init__(
            f"Agent {agent_id!r} attempted to call tool {tool_name!r} which is not "
            f"in its whitelist {sorted(allowed_tools)!r}"
        )


class Sandbox:
    """Tool whitelist enforcer.

    Parameters
    ----------
    agent_id:
        Identifier of the agent owning this sandbox.
    allowed_tools:
        Immutable set of tool names the agent may call.  An empty frozenset
        means the agent has *no* tool access.
    """

    def __init__(
        self,
        agent_id: str,
        allowed_tools: frozenset[str],
    ) -> None:
        self.agent_id = agent_id
        self.allowed_tools: frozenset[str] = allowed_tools

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def check(self, tool_name: str) -> None:
        """Assert that *tool_name* is permitted.

        Parameters
        ----------
        tool_name:
            The name of the tool the agent wants to call.

        Raises
        ------
        SandboxViolation
            If *tool_name* is not in :attr:`allowed_tools`.
        """
        if tool_name not in self.allowed_tools:
            log.warning(
                "sandbox.violation",
                agent_id=self.agent_id,
                tool_name=tool_name,
                allowed=sorted(self.allowed_tools),
            )
            raise SandboxViolation(
                agent_id=self.agent_id,
                tool_name=tool_name,
                allowed_tools=self.allowed_tools,
            )
        log.debug("sandbox.allowed", agent_id=self.agent_id, tool_name=tool_name)

    def validate_tool_call(self, call: ToolCall) -> None:
        """Validate a :class:`~hermes_orchestrator.schemas.ToolCall`.

        Convenience wrapper around :meth:`check`.

        Parameters
        ----------
        call:
            The tool call to validate.

        Raises
        ------
        SandboxViolation
            If the tool name is not whitelisted.
        """
        self.check(call.tool_name)

    def is_allowed(self, tool_name: str) -> bool:
        """Return ``True`` if *tool_name* is in the whitelist (non-raising)."""
        return tool_name in self.allowed_tools

    def __repr__(self) -> str:
        return f"Sandbox(agent_id={self.agent_id!r}, allowed_tools={sorted(self.allowed_tools)!r})"
