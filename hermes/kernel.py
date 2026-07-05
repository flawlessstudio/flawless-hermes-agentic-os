"""The Hermes kernel: a manual agentic loop over a pluggable provider.

Flow per step: send the conversation to the provider; if the model requested
tools, execute them all and return the results in a single user message; if
it produced a final answer, stop. A hard step limit bounds runaway loops.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from hermes.providers import Provider, ProviderResponse
from hermes.tools import ToolError, ToolRegistry

DEFAULT_SYSTEM = (
    "You are Hermes, a capable agent. Use the available tools when they help; "
    "answer directly when they don't. Be concise and factual."
)


@dataclass
class AgentResult:
    answer: str
    steps: int
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    stopped_early: bool = False


class Hermes:
    def __init__(
        self,
        provider: Provider,
        tools: ToolRegistry,
        system: str = DEFAULT_SYSTEM,
        max_steps: int = 20,
        on_event: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self._provider = provider
        self._tools = tools
        self._system = system
        self._max_steps = max_steps
        self._on_event = on_event or (lambda kind, data: None)

    def run(self, goal: str) -> AgentResult:
        messages: list[dict[str, Any]] = [{"role": "user", "content": goal}]
        tool_calls: list[dict[str, Any]] = []

        for step in range(1, self._max_steps + 1):
            response = self._provider.complete(
                self._system, messages, self._tools.schemas()
            )
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "tool_use":
                results = self._execute_tools(response, tool_calls)
                # All tool results must go back in ONE user message.
                messages.append({"role": "user", "content": results})
                continue

            if response.stop_reason == "refusal":
                self._on_event("refusal", {})
                return AgentResult(
                    answer="(the model declined this request)",
                    steps=step,
                    tool_calls=tool_calls,
                )

            return AgentResult(
                answer=_final_text(response),
                steps=step,
                tool_calls=tool_calls,
            )

        return AgentResult(
            answer="(step limit reached before the agent finished)",
            steps=self._max_steps,
            tool_calls=tool_calls,
            stopped_early=True,
        )

    def _execute_tools(
        self,
        response: ProviderResponse,
        tool_calls: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for block in response.content:
            if block.get("type") != "tool_use":
                continue
            name, tool_input = block["name"], block.get("input", {})
            self._on_event("tool_use", {"name": name, "input": tool_input})
            try:
                output = self._tools.execute(name, tool_input)
                is_error = False
            except ToolError as exc:
                output, is_error = f"Error: {exc}", True
            except TypeError as exc:
                # Bad/missing arguments from the model — recoverable.
                output, is_error = f"Error: invalid arguments: {exc}", True
            tool_calls.append(
                {"name": name, "input": tool_input, "output": output, "is_error": is_error}
            )
            self._on_event("tool_result", {"name": name, "output": output})
            result: dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": output,
            }
            if is_error:
                result["is_error"] = True
            results.append(result)
        return results


def _final_text(response: ProviderResponse) -> str:
    parts = [b["text"] for b in response.content if b.get("type") == "text"]
    return "\n".join(parts).strip()
