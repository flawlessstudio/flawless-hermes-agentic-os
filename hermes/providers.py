"""Model providers.

A provider turns (system, messages, tools) into a ``ProviderResponse`` whose
``content`` is a list of Messages-API-shaped content blocks (plain dicts:
``{"type": "text", ...}`` / ``{"type": "tool_use", ...}``). The kernel appends
those blocks back into the conversation verbatim, so whatever a provider
returns must be valid to send back to it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

DEFAULT_MODEL = "claude-opus-4-8"


@dataclass
class ProviderResponse:
    content: list[dict[str, Any]]
    stop_reason: str
    usage: dict[str, int] = field(default_factory=dict)


class Provider(Protocol):
    def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ProviderResponse: ...


class MockProvider:
    """Deterministic provider for tests and the offline demo.

    Takes a script of ``ProviderResponse`` objects and replays them in order.
    """

    def __init__(self, script: list[ProviderResponse]) -> None:
        self._script = list(script)
        self.calls: list[list[dict[str, Any]]] = []

    def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ProviderResponse:
        self.calls.append([dict(m) for m in messages])
        if not self._script:
            raise RuntimeError("MockProvider script exhausted")
        return self._script.pop(0)


class AnthropicProvider:
    """Calls Claude through the official ``anthropic`` SDK.

    Uses adaptive thinking (recommended for Opus 4.8) and returns content
    blocks as plain dicts, preserving thinking-block signatures so they can
    be replayed on subsequent turns.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 16000,
        client: Any | None = None,
    ) -> None:
        if client is None:
            try:
                import anthropic
            except ImportError as exc:
                raise RuntimeError(
                    "AnthropicProvider requires the 'anthropic' package: "
                    "pip install anthropic"
                ) from exc
            client = anthropic.Anthropic()
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ProviderResponse:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            thinking={"type": "adaptive"},
            tools=tools,
            messages=messages,
        )
        content: list[dict[str, Any]] = []
        for block in response.content:
            if block.type == "text":
                content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                content.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )
            elif block.type == "thinking":
                content.append(
                    {
                        "type": "thinking",
                        "thinking": block.thinking,
                        "signature": block.signature,
                    }
                )
            elif block.type == "redacted_thinking":
                content.append({"type": "redacted_thinking", "data": block.data})
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return ProviderResponse(
            content=content,
            stop_reason=response.stop_reason or "end_turn",
            usage=usage,
        )
