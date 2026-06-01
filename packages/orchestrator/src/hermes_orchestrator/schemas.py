"""Pydantic schemas for the hermes_orchestrator package."""

from __future__ import annotations

import enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MessagePriority(enum.IntEnum):
    """Priority levels for bus messages (lower = higher priority)."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class MessageStatus(str, enum.Enum):
    """Lifecycle status of a bus message."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"


class AgentMessage(BaseModel):
    """A typed message sent over the :class:`~hermes_orchestrator.bus.AsyncMessageBus`."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    sender_id: str
    recipient_id: str | None = None  # None = broadcast
    topic: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    correlation_id: str | None = None


class ToolCall(BaseModel):
    """Represents a single tool invocation by an agent."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    call_id: str = Field(default_factory=lambda: str(uuid4()))


class ToolResult(BaseModel):
    """Result of executing a :class:`ToolCall`."""

    call_id: str
    tool_name: str
    success: bool
    result: Any = None
    error: str | None = None


class AgentConfig(BaseModel):
    """Static configuration for an agent instance."""

    agent_id: str
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 8192
    allowed_tools: frozenset[str] = Field(default_factory=frozenset)
    system_prompt: str = ""
    temperature: float = 1.0

    model_config = {"frozen": True}
