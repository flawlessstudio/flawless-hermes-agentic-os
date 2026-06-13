# Flawless Hermes Agentic OS

> Local-first Mission Control scaffold for observing agent roles with explicit permission boundaries.

[![CI](https://github.com/flawlessstudio/flawless-hermes-agentic-os/actions/workflows/ci.yml/badge.svg)](https://github.com/flawlessstudio/flawless-hermes-agentic-os/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE.md)

## Current status

```text
Phase: executable scaffold under validation
Dashboard: implemented
Agent status: deterministic mock
Real adapters: disabled
Privileged capabilities: disabled or approval-gated by policy
Credentials required: no
Public-production readiness: not claimed
```

The repository now contains a real Next.js application, but it does **not** yet orchestrate Claude Code, OpenClaw, Hermes Agent or an Obsidian vault. Those integrations remain future, separately reviewed adapters.

## Implemented scope

- Next.js 15 / React 19 / TypeScript application scaffold.
- Responsive Mission Control interface.
- `GET /api/health` application-health endpoint.
- `GET /api/agents` deterministic mock-status endpoint.
- Typed agent-status contract.
- Deny-by-default capability policy.
- Tests for permission boundaries.
- ESLint, type checking, tests, build and dependency-audit gates.
- Architecture, permissions and validation documentation.

## Explicitly not implemented

- autonomous orchestration;
- real agent process control;
- vault-content access;
- external communication;
- repository or system changes;
- billable API calls;
- background daemons;
- remote gateway exposure.

## Architecture

```text
Browser
  ↓
Next.js Mission Control
  ├── /api/health       application status
  ├── /api/agents       mock agent status
  ├── agent contracts   typed read model
  └── policy module     allow / approval-required / deny
```

See [`docs/architecture.md`](docs/architecture.md) and [`docs/permissions.md`](docs/permissions.md).

## Stack contract

| Area | Technology |
|---|---|
| Application | Next.js 15, React 19, TypeScript |
| Styling | Tailwind CSS 4, custom responsive CSS |
| Motion | Framer Motion |
| Tests | Vitest |
| Runtime | Node.js 22.19+; Node 24 recommended |

## Quickstart

```bash
git clone https://github.com/flawlessstudio/flawless-hermes-agentic-os.git
cd flawless-hermes-agentic-os
nvm use
npm ci
npm run dev
```

Open `http://localhost:3000`.

The scaffold runs without `.env.local`, API keys, local agents or paid services.

## Validation

```bash
npm run lint
npm run type-check
npm run test
npm run build
npm audit --audit-level=high
```

The authoritative validation state is recorded in [`docs/validation.md`](docs/validation.md). A badge alone is not treated as evidence; the workflow must pass against the current commit and committed lockfile.

## Permission model

| Decision | Meaning |
|---|---|
| `allow` | Bounded read-only capability |
| `approval-required` | Consequential capability requiring explicit authorization |
| `deny` | Unavailable capability |

Any undeclared capability resolves to `deny`.

## API responses

### `GET /api/health`

Returns application phase, timestamp and whether adapters are enabled.

### `GET /api/agents`

Returns the typed mock status for the declared agent layers. It does not probe local processes or external services.

## Project structure

```text
src/
├── app/
│   ├── api/health/route.ts
│   ├── api/agents/route.ts
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx
├── components/mission-control.tsx
└── lib/
    ├── agents/
    └── policy/

tests/permissions.test.ts
docs/architecture.md
docs/permissions.md
docs/validation.md
```

## Future adapters

A real adapter may be introduced only after:

1. its local interface and trust boundary are documented;
2. permissions and credentials are minimized;
3. approval, timeout, cancellation and recovery behavior are defined;
4. tests cover normal, error and unauthorized paths;
5. CI passes against the real integration;
6. the documentation is updated from mock to observed behavior.

## Security

Never commit credentials. Report sensitive issues through [`SECURITY.md`](SECURITY.md).

## License

MIT © 2026 Flawless Studio
