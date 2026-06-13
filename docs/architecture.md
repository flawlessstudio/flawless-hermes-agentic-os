# Architecture

## Current phase

```text
Phase: executable local scaffold
Runtime: Next.js server-rendered dashboard
Status source: deterministic mock provider
External adapters: disabled
Stateful operations: absent
Paid services: not required
```

## Runtime boundaries

```text
Browser
  ↓
Next.js application
  ├── /api/health
  ├── /api/agents
  ├── typed status model
  └── runtime feature policy
```

The current application does not connect to local agents, gateways or vault content. Those systems remain future adapter boundaries.

## Design rules

1. Local-first by default.
2. Observation before control.
3. Features disabled unless explicitly enabled.
4. No credential requirement for the mock runtime.
5. Adapter logic remains separate from the interface.
6. Future adapters require validation, timeout, recovery and tests.

## Out of scope

- autonomous orchestration;
- process control;
- content mutation;
- remote publication;
- paid calls;
- remote exposure.
