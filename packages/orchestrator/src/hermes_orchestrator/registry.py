"""AgentRegistry — thread-safe registry of active agent instances."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from hermes_orchestrator.agent import BaseAgent

log = structlog.get_logger(__name__)


class RegistrationError(Exception):
    """Raised when an agent cannot be registered."""


class AgentRegistry:
    """Central registry tracking all active :class:`~hermes_orchestrator.agent.BaseAgent` instances.

    Thread-safe via a reentrant lock.

    Usage::

        registry = AgentRegistry()
        registry.register(my_agent)
        agent = registry.get("my_agent_id")
        registry.deregister("my_agent_id")
    """

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def register(self, agent: BaseAgent) -> None:
        """Add *agent* to the registry.

        Parameters
        ----------
        agent:
            The agent instance to register.  Must have a unique ``config.agent_id``.

        Raises
        ------
        RegistrationError
            If an agent with the same ID is already registered.
        """
        with self._lock:
            aid = agent.config.agent_id
            if aid in self._agents:
                raise RegistrationError(f"Agent {aid!r} is already registered.")
            self._agents[aid] = agent
            log.info("agent_registry.registered", agent_id=aid)

    def deregister(self, agent_id: str) -> bool:
        """Remove an agent from the registry.

        Parameters
        ----------
        agent_id:
            The ID of the agent to remove.

        Returns
        -------
        bool
            ``True`` if the agent was found and removed.
        """
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                log.info("agent_registry.deregistered", agent_id=agent_id)
                return True
            return False

    def get(self, agent_id: str) -> BaseAgent | None:
        """Retrieve an agent by ID, or ``None`` if not registered."""
        with self._lock:
            return self._agents.get(agent_id)

    def list_ids(self) -> list[str]:
        """Return a sorted list of all registered agent IDs."""
        with self._lock:
            return sorted(self._agents.keys())

    def count(self) -> int:
        """Return the number of registered agents."""
        with self._lock:
            return len(self._agents)

    def clear(self) -> None:
        """Deregister all agents."""
        with self._lock:
            count = len(self._agents)
            self._agents.clear()
            log.info("agent_registry.cleared", removed=count)

    def __contains__(self, agent_id: object) -> bool:
        with self._lock:
            return agent_id in self._agents

    def __repr__(self) -> str:
        with self._lock:
            return f"AgentRegistry(agents={self.list_ids()!r})"
