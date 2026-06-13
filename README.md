# Flawless Hermes Agentic OS

> Local-first Mission Control scaffold for observing declared system layers with explicit runtime boundaries.

## Current status

```text
Phase: executable scaffold under validation
Dashboard: implemented
Status data: deterministic mock
Local adapters: disabled
Content access: disabled
Stateful actions: disabled
Paid services: disabled
Credentials required: no
Public-production readiness: not claimed
```

The repository contains a real Next.js application. It does not yet connect to Claude Code, OpenClaw, Hermes Agent or an Obsidian vault; those names define future adapter boundaries, not active integrations.

## Implemented scope

- Next.js 15 / React 19 / TypeScript application.
- Responsive server-rendered Mission Control interface.
- `GET /api/health` application-health endpoint.
- `GET /api/agents` deterministic mock-status endpoint.
- Typed status contract.
- Explicit runtime feature policy.
- Automated policy-boundary tests.
- ESLint, type checking, tests, build and dependency-audit gates.
- Architecture, policy and validation documentation.

## Explicitly excluded

- autonomous orchestration;
- real process or gateway control;
- vault-content access;
- stateful operations;
- external publishing;
- paid API use;
- background daemons;
- remote exposure.

## Architecture

```text
Browser
  ↓
Next.js Mission Control
  ├── /api/health       application status
  ├── /api/agents       mock layer status
  ├── typed read model
  └── runtime policy    enabled / disabled features
```

## Stack

| Area | Technology |
|---|---|
| Application | Next.js 15, React 19, TypeScript |
| Styling | Tailwind CSS 4 and custom responsive CSS |
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

The scaffold runs without `.env.local`, local agents or paid services.

## Validation

```bash
npm run lint
npm run type-check
npm run test
npm run build
npm audit --audit-level=high
```

The CI badge is not sufficient evidence by itself. Validation requires the current committed lockfile and successful gates against the current commit.

## Runtime policy

Only `statusPanel` and `metadataPanel` are enabled. Content access, adapter calls, state changes and paid services remain disabled in `src/lib/policy/runtime.ts` and are verified by `tests/runtime-policy.test.ts`.

## Future adapter entry criteria

A real adapter may be introduced only after its interface and trust boundary are documented, inputs and outputs are validated, timeout and recovery behavior exist, relevant paths are tested and CI passes against the real implementation.

## Security

Never commit credentials. See [`SECURITY.md`](SECURITY.md).

## License

MIT © 2026 Flawless Studio
