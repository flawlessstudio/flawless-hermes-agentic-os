"""CLI entry point: ``python -m hermes "your goal"`` or ``python -m hermes --demo``."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from hermes.kernel import Hermes
from hermes.providers import DEFAULT_MODEL, AnthropicProvider, MockProvider, ProviderResponse
from hermes.tools import builtin_registry


def _print_event(kind: str, data: dict[str, Any]) -> None:
    if kind == "tool_use":
        print(f"  -> {data['name']}({data['input']})", file=sys.stderr)
    elif kind == "tool_result":
        preview = data["output"][:120].replace("\n", " ")
        print(f"  <- {preview}", file=sys.stderr)


def _demo_provider() -> MockProvider:
    """A scripted run that exercises the full loop without a network call."""
    return MockProvider(
        [
            ProviderResponse(
                content=[
                    {"type": "text", "text": "I'll compute that with the calculator."},
                    {
                        "type": "tool_use",
                        "id": "demo_1",
                        "name": "calculator",
                        "input": {"expression": "(17 * 23) + 4"},
                    },
                ],
                stop_reason="tool_use",
            ),
            ProviderResponse(
                content=[{"type": "text", "text": "(17 * 23) + 4 = 395."}],
                stop_reason="end_turn",
            ),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hermes", description="Run a goal through the Hermes agent kernel."
    )
    parser.add_argument("goal", nargs="?", help="the goal to accomplish")
    parser.add_argument(
        "--demo", action="store_true", help="run a scripted offline demo (no API key)"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Claude model id")
    parser.add_argument(
        "--workspace", default=".", help="directory the file tools are sandboxed to"
    )
    parser.add_argument("--max-steps", type=int, default=20)
    args = parser.parse_args(argv)

    if args.demo:
        provider: Any = _demo_provider()
        goal = args.goal or "What is (17 * 23) + 4?"
    elif args.goal:
        try:
            provider = AnthropicProvider(model=args.model)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        goal = args.goal
    else:
        parser.print_usage(sys.stderr)
        print("error: provide a goal, or use --demo", file=sys.stderr)
        return 2

    agent = Hermes(
        provider,
        builtin_registry(args.workspace),
        max_steps=args.max_steps,
        on_event=_print_event,
    )
    result = agent.run(goal)
    print(result.answer)
    return 0 if not result.stopped_early else 3


if __name__ == "__main__":
    sys.exit(main())
