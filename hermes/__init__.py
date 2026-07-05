"""Hermes Agentic OS — a minimal kernel for Claude-powered agents."""

from hermes.kernel import AgentResult, Hermes
from hermes.providers import AnthropicProvider, MockProvider, ProviderResponse
from hermes.tools import ToolError, ToolRegistry, builtin_registry

__version__ = "0.1.0"

__all__ = [
    "AgentResult",
    "AnthropicProvider",
    "Hermes",
    "MockProvider",
    "ProviderResponse",
    "ToolError",
    "ToolRegistry",
    "builtin_registry",
]
