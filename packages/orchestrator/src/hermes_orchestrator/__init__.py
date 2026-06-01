"""hermes_orchestrator — agent bus, sandbox enforcement, and registry.

Public API
----------
- BaseAgent      : Abstract base class for Claude-backed agents
- AsyncMessageBus: Priority async message bus with DLQ
- AgentRegistry  : Thread-safe agent instance registry
- Sandbox        : Tool whitelist enforcement gate
- SandboxViolation: Exception raised on whitelist violation
- AgentConfig, AgentMessage, ToolCall, ToolResult: Pydantic schemas
"""

from hermes_orchestrator.agent import BaseAgent
from hermes_orchestrator.bus import AsyncMessageBus
from hermes_orchestrator.registry import AgentRegistry
from hermes_orchestrator.sandbox import Sandbox, SandboxViolation
from hermes_orchestrator.schemas import (
    AgentConfig,
    AgentMessage,
    MessagePriority,
    ToolCall,
    ToolResult,
)

__all__ = [
    "AgentConfig",
    "AgentMessage",
    "AgentRegistry",
    "AsyncMessageBus",
    "BaseAgent",
    "MessagePriority",
    "Sandbox",
    "SandboxViolation",
    "ToolCall",
    "ToolResult",
]
