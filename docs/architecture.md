# Architecture

## Current phase

```text
Phase: verified local scaffold candidate
Runtime: Next.js dashboard
Agent data: deterministic mock provider
External adapters: disabled
Privileged execution: absent
Paid services: not required
```

## Runtime boundaries

```text
Browser
  ↓
Next.js application
  ├── /api/health       read-only application status
  ├── /api/agents       read-only mock agent status
  ├── agent contracts   typed status model
  └── policy module     explicit capability decisions
```

The current application does not connect to Claude Code, OpenClaw, Hermes Agent or an Obsidian vault. Those names describe intended future adapter boundaries, not active integrations.

## Design rules

1. Local-first by default.
2. Read-only status before control capabilities.
3. Deny by default for undeclared capabilities.
4. Explicit approval for consequential capabilities.
5. No irreversible data capability in the scaffold.
6. No credential requirement for the mock runtime.
7. Adapter implementation must remain separate from UI components.
8. Every future adapter requires input validation, timeout, cancellation, failure handling and tests.

## Planned adapter contract

A future local adapter may return `AgentStatusResponse` only after it has been separately reviewed and enabled. The UI must not infer operational status from documentation or process presence alone.

## Out of scope

- autonomous orchestration;
- command execution;
- package installation;
- repository changes;
- external communications;
- paid API use;
- vault-content access;
- background daemons;
- remote exposure.
