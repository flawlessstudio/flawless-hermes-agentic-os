# Hermes Agentic OS

**A minimal, dependency-free kernel for building Claude-powered agents.**

Hermes is the smallest useful core of an "agentic operating system": an agent
receives a goal, reasons about it, executes tools in a loop, and reports back.
Everything else — schedulers, memory, multi-agent orchestration — is layered on
top of this kernel later, not baked in before it works.

> **Status: pre-alpha.** The kernel works end-to-end (goal → tool calls →
> answer) with a mock provider for offline testing and an Anthropic provider
> for real runs. APIs will change.

## What exists today

- **`hermes.kernel`** — the agent loop. Sends the conversation to a model
  provider, executes any requested tools, feeds results back, and repeats
  until the model produces a final answer (or a step limit is hit).
- **`hermes.tools`** — a tool registry with JSON-Schema definitions and a few
  built-in tools (calculator, workspace file reading).
- **`hermes.providers`** — pluggable model backends:
  - `AnthropicProvider` — calls Claude (`claude-opus-4-8` by default) via the
    official `anthropic` SDK with adaptive thinking.
  - `MockProvider` — scripted responses, zero network, used by the test suite.

## Quick start

```bash
# Offline demo (no API key required)
python -m hermes --demo

# Real run (requires: pip install anthropic, and ANTHROPIC_API_KEY set)
python -m hermes "What is (17 * 23) + 4? Use the calculator."

# Tests
python -m unittest discover -s tests -v
```

## Design principles

1. **Kernel before OS.** One working process (goal → tools → answer) before
   any scheduler, daemon, or multi-agent ambition.
2. **Zero required dependencies.** The core is stdlib-only; the Anthropic SDK
   is an optional extra for real model calls.
3. **Providers are pluggable.** The kernel speaks a small protocol
   (`complete(system, messages, tools) -> ProviderResponse`), so any model —
   or a deterministic mock — can drive it.
4. **Tools are the security boundary.** Built-in tools are sandboxed to the
   working directory; the calculator evaluates AST nodes, not `eval()`.

## Roadmap (deliberately short)

- [x] Agent loop with tool use (this release)
- [ ] Streaming output in the CLI
- [ ] Persistent memory file the agent reads/writes across runs
- [ ] Sub-agent spawning (one level)

## License

Apache-2.0 — see [LICENSE.md](LICENSE.md).
