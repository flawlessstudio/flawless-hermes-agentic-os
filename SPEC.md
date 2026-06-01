# Hermes Agent OS — Full System Specification

Version: 1.0.0 | Branch: claude/busy-fermi-8Wnn2 | Date: 2026-06-01

---

## 1. Mission & Principles

Hermes Agent OS is a **local-first, production-grade Agent Operating System** designed to run
specialized AI agents with persistent memory, atomic state, and a Mission Control dashboard.

### The Flawless Method
1. **Zero Placeholders** — every file ships complete and functional
2. **Gate-Driven** — each phase has a measurable GATE condition; nothing advances without passing
3. **Local-First** — all data stays on-device by default; cloud is opt-in
4. **Atomic Everything** — every write is crash-safe (temp → fsync → rename)
5. **Security by Design** — sandboxed agents, no secrets in code, Semgrep CI
6. **WCAG AA** — all UI components meet accessibility standards
7. **Observability** — structured logs, OpenTelemetry traces, health endpoints
8. **Human Pause (PAUSA HUMANA)** — destructive ops and payment ops require explicit human confirmation

---

## 2. System Architecture

### Ecosystem Planes

| Plane | Label | Contents |
|-------|-------|----------|
| A | Storage | AtomicStore (SQLite WAL), FileLock, CheckpointManager |
| B | Memory | VectorMemory (ChromaDB), GraphMemory (SQLite), MemoryManager |
| C | Orchestration | BaseAgent, AsyncMessageBus, AgentRegistry, ToolSandbox |
| D | Skills/MCP | MCP connectors, tool registry, PAUSA HUMANA gates |
| E | API | FastAPI backend, SSE streaming, health/agents/memory routes |
| F | UI | Next.js Mission Control, AgentGrid, ActivityFeed, MemoryPanel |

### Technology Stack

**Backend**
- Python 3.12+ with strict mypy
- FastAPI 0.115+ with Pydantic v2
- uv for dependency management and virtual environments
- structlog for structured logging
- OpenTelemetry for distributed tracing
- SQLite with WAL mode (no external database required)
- ChromaDB for local vector storage

**Frontend**
- Next.js 15 (App Router) with React 19
- TypeScript strict mode + noUncheckedIndexedAccess
- Tailwind CSS 4
- Radix UI primitives for accessible components
- Vitest + Playwright for testing

**Agents**
- Claude Sonnet 4.6 (claude-sonnet-4-6) via Anthropic SDK
- Tool use with sandboxed ALLOWED_TOOLS per agent
- Async message bus for inter-agent communication

---

## 3. Phase Definitions

### F0 — Bootstrap
**Goal**: Working monorepo scaffold with correct tooling.

Files: pyproject.toml (workspace), Makefile, README.md, CLAUDE.md, SPEC.md, .gitignore, pnpm-workspace.yaml

GATE: `make install` completes without errors. All packages importable.

### F1 — Atomic State Store
**Goal**: Crash-safe key-value store with WAL SQLite.

Files: packages/core/src/hermes_core/{store,checkpoint,lock,exceptions,__init__}.py

Key invariants:
- Write path: acquire lock → backup → write to temp → fsync → rename → release
- SIGKILL between any two steps leaves previous state intact
- History table records all mutations with timestamps

GATE: `test_durability.py` — store survives SIGKILL mid-write. `test_store.py` — all 10 assertions pass.

### F2 — Persistent Memory
**Goal**: Vector + graph memory for semantic recall and knowledge graphs.

Files: packages/memory/src/hermes_memory/{vector,graph,manager,schemas,__init__}.py

Key features:
- VectorMemory: ChromaDB PersistentClient with cosine similarity, per-agent collections
- GraphMemory: SQLite with BFS/DFS traversal, nodes + edges schema
- MemoryManager: unified API combining both backends
- Persistence across process restarts (tested by test_round_trip_persistence)

GATE: `test_memory.py` — round-trip persist/recall passes.

### F3 — Agent Orchestrator
**Goal**: Sandbox-enforced agent bus with type-safe messaging.

Files: packages/orchestrator/src/hermes_orchestrator/{agent,bus,registry,sandbox,schemas,exceptions,__init__}.py

Security invariant: An agent may ONLY call tools in its ALLOWED_TOOLS frozenset.
Violation raises SandboxViolation immediately — not configurable, not bypassable.

GATE: `test_sandbox.py` — all sandbox violation tests pass.

### F4 — Skills/MCP Config
**Goal**: Documented MCP connector catalog with security tiers.

Files: config/mcp.example.json, INSTALL_LOG.md

Security gate §10.7:
1. Source verified (GitHub org + commit hash)
2. License compatible (MIT, Apache-2.0, LGPL acceptable)
3. Secrets via environment only (PAUSA HUMANA for tokens)
4. Tier assigned (0 = official/high-trust, 1 = community, 2 = experimental)
5. Logged in INSTALL_LOG.md

GATE: All MCP servers in mcp.example.json have tier, source, and license documented.

### F5 — Backend API
**Goal**: FastAPI backend with health, agents, memory, and SSE endpoints.

Files: packages/api/src/hermes_api/{main,middleware,logging,routes/{health,agents,memory,stream},__init__}.py

Endpoints:
- GET /health — system health with component status
- GET /ready — readiness probe
- GET /agents/ — list registered agents
- GET /agents/{id} — get agent info
- POST /memory/query — semantic search
- POST /memory/store — store memory entry
- GET /stream/events — SSE event stream

GATE: `test_api.py` — health endpoint returns 200. All routes registered.

### F6 — Mission Control UI
**Goal**: Real-time dashboard for agent monitoring and memory search.

Files: apps/mission-control/src/{app,components,lib,hooks}/...

Components:
- StatusBar: connection indicator with SSE status
- AgentGrid: responsive grid of AgentCard components
- AgentCard: agent status, tools, message count
- ActivityFeed: live SSE event stream
- MemoryPanel: semantic memory search interface
- Skeleton: loading states for all cards

GATE: `pnpm build` succeeds. No TypeScript errors. WCAG AA maintained.

### F7 — UX/Flows
**Goal**: Smooth loading states, error boundaries, empty states, a11y.

Key requirements:
- Every async component has a skeleton loading state
- All errors shown with role="alert"
- All empty states with descriptive copy
- Skip-to-content link in layout
- All interactive elements keyboard-accessible

GATE: Lighthouse a11y score ≥ 90.

### F8 — Branding
**Goal**: Consistent Hermes visual identity across all surfaces.

Design tokens (CSS custom properties):
- --color-bg, --color-surface, --color-surface-2
- --color-border, --color-text, --color-text-muted
- --color-accent (purple #7c3aed), --color-success/warning/error/info
- Contrast ratios: all text/background pairs meet WCAG AA (4.5:1 minimum)

GATE: Zero contrast violations in automated a11y audit.

### F9 — Security/Hardening
**Goal**: CI security scanning, no secrets, HTTP security headers.

Files: .github/workflows/{ci,security}.yml, .github/PULL_REQUEST_TEMPLATE.md

Requirements:
- TruffleHog secret scan on every PR
- Semgrep SAST on every push
- OSV dependency vulnerability scan weekly
- X-Frame-Options: DENY on all responses
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin

GATE: CI passes on branch. No secrets detected by TruffleHog.

### F10 — Observability
**Goal**: Structured logs, request tracing, health monitoring.

Requirements:
- structlog configured with ISO timestamps and log level
- Request ID injected into every request/response via middleware
- All log lines include request_id, method, path, status, duration_ms
- Health endpoint reports per-component status

GATE: All API requests produce structured log lines with request_id.

### F11 — Packaging/Delivery
**Goal**: Production build, Docker-ready, documented deployment.

Requirements:
- `make build` produces deployable artifacts
- `make check` runs all gates in sequence
- docs/runbook.md covers full deployment procedure
- pnpm-workspace.yaml + uv workspace correctly defined

GATE: `make check` passes from clean checkout.

---

## 4. Agent Definitions

### Research Agent
- **ID**: research
- **Purpose**: Information gathering, synthesis, summarization
- **Tools**: web_search, fetch_url, read_file, summarize, store_memory, recall_memory
- **Constraints**: Must cite sources; must flag uncertainty; no hallucination

### Code Agent
- **ID**: code
- **Purpose**: Software engineering tasks
- **Tools**: read_file, write_file, run_tests, lint, git_status, git_diff, search_code
- **Constraints**: Strict TypeScript/Python only; must add tests; no secrets

### Ops Agent
- **ID**: ops
- **Purpose**: System health, monitoring, deployment coordination
- **Tools**: health_check, get_logs, get_metrics, list_deployments
- **Constraints**: NEVER destructive ops without human confirmation; escalate anomalies immediately

---

## 5. Security Model

### §10.7 MCP Security Gate

Every MCP connector installation must pass:

1. **Source verification**: GitHub org/repo identified and trusted
2. **License check**: MIT, Apache-2.0, or LGPL-2.1+ only
3. **Secret handling**: All tokens via environment variables only
4. **Tier classification**:
   - Tier 0: Official (Anthropic, Microsoft, first-party)
   - Tier 1: Community (known maintainer, >100 GitHub stars)
   - Tier 2: Experimental (unvetted — requires manual review per use)
5. **INSTALL_LOG.md entry**: All fields populated before activation

### PAUSA HUMANA Protocol

Operations requiring explicit human confirmation before execution:
- Any payment processing (Stripe, etc.)
- Destructive database operations (DROP, DELETE without WHERE)
- Production deployments
- Sending external communications (email, Slack to external)
- Any operation involving PII export

Implementation: agent pauses, presents intent + consequences, waits for explicit "confirm" message.

### Sandbox Enforcement

The `ToolSandbox.check(tool_name)` method is called at the agent base class level
before any tool execution. This cannot be overridden by subclasses — the check
happens in `BaseAgent.call_tool()` which calls `self._sandbox.check()` before
delegating to `_execute_tool()`.

---

## 6. Data Architecture

### AtomicStore Write Path
```
acquire_lock()
  backup(path → path.bak)
  write(data → temp_file)
  fsync(temp_file)
  rename(temp_file → path)
release_lock()
reindex()
```

### Memory System
```
MemoryManager
├── VectorMemory (ChromaDB)
│   ├── Collection per agent_id
│   ├── Cosine similarity search
│   └── Metadata filtering
└── GraphMemory (SQLite)
    ├── nodes table (id, label, properties, ts)
    ├── edges table (source, target, relation, weight, ts)
    └── BFS/DFS traversal
```

### Message Bus
```
AsyncMessageBus
├── PriorityQueue (CRITICAL=0, HIGH=1, NORMAL=2, LOW=3)
├── Per-agent subscription handlers
├── Dead letter queue for failed deliveries
└── Bounded queue (back-pressure at 1000 messages)
```

---

## 7. API Contract

### Health Response
```json
{
  "status": "ok",
  "version": "0.1.0",
  "ts": 1748789000.0,
  "components": {
    "store": "ok",
    "memory": "ok",
    "orchestrator": "ok"
  }
}
```

### Agent Info
```json
{
  "id": "research",
  "status": "idle|running|error|paused",
  "allowed_tools": ["web_search", "fetch_url"],
  "message_count": 42,
  "last_active": 1748789000.0
}
```

### Memory Query
```json
POST /memory/query
{
  "query": "user preferences for programming language",
  "agent_id": "global",
  "top_k": 5
}
```

### SSE Events
```
data: {"ts": 1748789000.0, "type": "heartbeat"}

data: {"ts": 1748789001.0, "type": "agent_message", "agent": "research", "message": "Starting research..."}
```

---

## 8. Definition of Done

A phase is DONE when:
1. All files listed for that phase exist and are non-empty
2. The GATE condition passes (test, build, or manual verification)
3. No mypy errors in Python files (strict mode)
4. No TypeScript errors (`tsc --noEmit`)
5. No ruff violations
6. INSTALL_LOG.md updated (if new dependencies added)
7. CheckpointManager.mark_passed(phase) called in build script

---

## 9. Extension Points

### Adding a New Agent
1. Create `agents/{name}/agent.py` extending `BaseAgent`
2. Define `AGENT_ID`, `ALLOWED_TOOLS`, `system_prompt`
3. Implement `_execute_tool()` and `_handle_message()`
4. Register in `AgentRegistry` at startup
5. Add agent tools to `config/mcp.example.json` if MCP-backed
6. Update INSTALL_LOG.md

### Adding a New MCP Connector
1. Evaluate via §10.7 security gate
2. Add to `config/mcp.example.json` with all metadata fields
3. Add to INSTALL_LOG.md
4. Wire tools to relevant agent's `_execute_tool()` implementation
5. Add integration test

### Adding a New API Route
1. Create `packages/api/src/hermes_api/routes/{name}.py`
2. Define router with prefix and tags
3. Include in `main.py` via `app.include_router()`
4. Add Pydantic request/response models to `schemas.py`
5. Add tests to `packages/api/tests/test_{name}.py`
