# Hermes Agent OS — Architecture

## System Overview

Hermes Agent OS is a local-first, production-grade Agent Operating System. It runs
specialized AI agents (backed by Claude Sonnet 4.6) with persistent memory, atomic state
management, and a real-time Mission Control dashboard.

All data is stored locally by default. Cloud connectivity is opt-in and requires explicit
configuration.

## Component Diagram (ASCII)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Mission Control (Next.js 15)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────┐  │
│  │  StatusBar   │  │  AgentGrid   │  │ ActivityFeed│  │MemoryPanel│ │
│  │  (SSE conn)  │  │  (AgentCard) │  │ (SSE events)│  │(search UI)│ │
│  └──────────────┘  └──────────────┘  └────────────┘  └──────────┘  │
│                          ↑ HTTP / SSE                                │
└──────────────────────────│──────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│                      FastAPI Backend (Plane E)                       │
│  /health  /agents  /memory/query  /memory/store  /stream/events      │
│  ┌─────────────────────┐  ┌────────────────────────────────────────┐ │
│  │  RequestIDMiddleware │  │         CORS (localhost only)          │ │
│  └─────────────────────┘  └────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
│  AtomicStore     │ │  MemoryMgr   │ │  AgentRegistry   │
│  (Plane A)       │ │  (Plane B)   │ │  (Plane C)       │
│                  │ │              │ │                  │
│  SQLite WAL      │ │ VectorMemory │ │  AsyncMessageBus │
│  FileLock        │ │ (ChromaDB)   │ │  ToolSandbox     │
│  CheckpointMgr   │ │              │ │  BaseAgent       │
│                  │ │ GraphMemory  │ │                  │
│  .db + .bak      │ │ (SQLite)     │ │  ResearchAgent   │
└──────────────────┘ └──────────────┘ │  CodeAgent       │
                                      │  OpsAgent        │
                                      └────────┬─────────┘
                                               │
                                      ┌────────▼─────────┐
                                      │  Anthropic API   │
                                      │  (claude-sonnet  │
                                      │   -4-6)          │
                                      └──────────────────┘
```

## Data Flows

### Agent Task Execution
1. User sends task via Mission Control UI
2. POST /agents/{id}/run → FastAPI route
3. Route looks up agent in AgentRegistry
4. Agent.run(message) → Anthropic API call
5. Claude responds with tool_use blocks
6. BaseAgent calls Sandbox.check(tool_name) — raises SandboxViolation if denied
7. Tool executed via MCP connector
8. Result fed back to Claude for next turn
9. Final text response streamed via SSE to UI

### Memory Storage
1. Agent calls store_memory tool
2. MemoryManager.remember(content, metadata)
3. VectorMemory.add(MemoryEntry) → ChromaDB upsert
4. Content embedded and stored with agent_id + timestamp

### Memory Retrieval
1. Agent calls recall_memory tool with query
2. MemoryManager.recall(query, top_k=5)
3. VectorMemory.search(query) → cosine similarity
4. Top-k results returned with scores
5. Agent uses results to inform response

### Atomic Write Path
```
1. acquire FileLock (POSIX flock, timeout 10s)
2. backup(db → db.bak)
3. write data to temp file (mkstemp in same dir)
4. fsync(temp file)
5. os.rename(temp → db)  [atomic on POSIX]
6. release FileLock
```

## Technology Choices

### Python + FastAPI
- FastAPI chosen for async-native design, Pydantic v2 integration, and excellent DX
- uv for fast, deterministic dependency resolution
- structlog for structured, context-aware logging
- mypy strict mode enforces type safety across all packages

### SQLite WAL Mode
- WAL (Write-Ahead Logging) enables concurrent reads during writes
- PRAGMA synchronous=FULL ensures fsync on every write
- No external database server required — fully local-first
- Backup file (.bak) enables recovery from corruption

### ChromaDB
- PersistentClient mode — all data stored locally, no cloud required
- Cosine similarity for semantic search
- Per-agent collections provide isolation
- anonymized_telemetry=False — no data leaves the machine

### Next.js 15 + React 19
- App Router for server/client component separation
- TypeScript strict mode + noUncheckedIndexedAccess
- Radix UI primitives for accessible components (WCAG AA)
- SSE via EventSource for real-time agent events

## Security Model

### Agent Sandbox
Every agent declares ALLOWED_TOOLS (frozenset). The Sandbox.check() method is called
in BaseAgent.run() before any tool execution. This is enforced in the base class and
cannot be overridden by subclasses.

```python
# In BaseAgent.run() — cannot be bypassed
self._sandbox.check(tool_call.tool_name)  # raises SandboxViolation if denied
```

### PAUSA HUMANA Protocol
Certain operations require explicit human confirmation:
- Payment processing (Stripe)
- Production deployments
- Destructive database operations
- PII export

Implementation: agent sends message to bus with topic="human_pause_required",
pauses execution, waits for confirmation message.

### HTTP Security Headers
All responses include:
- X-Frame-Options: DENY (prevents clickjacking)
- X-Content-Type-Options: nosniff (prevents MIME sniffing)
- Referrer-Policy: strict-origin-when-cross-origin

### Secrets Management
- Zero secrets in code (enforced by TruffleHog scan in CI)
- All API keys via environment variables
- PAUSA HUMANA required for any new credential

## Memory System Design

### Dual-Backend Architecture
```
MemoryManager
├── VectorMemory (semantic)
│   ├── ChromaDB PersistentClient
│   ├── One collection per agent_id
│   ├── Cosine similarity (hnsw:space=cosine)
│   └── Full-text + semantic hybrid
└── GraphMemory (structural)
    ├── SQLite (nodes + edges)
    ├── BFS traversal (up to max_depth hops)
    └── DFS traversal
```

### Agent Isolation
Each agent gets its own ChromaDB collection: `agent_{agent_id}`. This prevents
cross-agent memory contamination. The "global" collection is shared across agents
for system-wide knowledge.

## API Design

RESTful with SSE for streaming. All endpoints return Pydantic models.
Request IDs injected by RequestIDMiddleware for tracing.

### Error Responses
All errors return ErrorResponse with error, detail, and request_id fields.
HTTP status codes follow RFC 7807.

## Frontend Architecture

```
apps/mission-control/
├── src/
│   ├── app/           # Next.js App Router (layout, page, globals.css)
│   ├── components/    # React components (AgentCard, AgentGrid, etc.)
│   ├── hooks/         # React hooks (useAgents, useSSE)
│   └── lib/           # Utilities (api.ts, utils.ts)
```

Design system uses CSS custom properties for theming. All colors meet WCAG AA
contrast requirements. Components use Radix UI primitives for accessible behavior.

## CI/CD Pipeline

```
push → GitHub Actions
  ├── python-lint (ruff + mypy)
  ├── python-test (pytest + coverage)
  ├── node-lint (tsc + eslint)
  ├── node-test (vitest)
  └── secret-scan (TruffleHog)

weekly → security workflow
  ├── semgrep SAST
  └── osv-scanner dependency audit
```

## Extension Points

### New Agent
1. Extend BaseAgent in agents/{name}/agent.py
2. Define ALLOWED_TOOLS and implement handle_tool()
3. Register in AgentRegistry at startup

### New MCP Connector
1. Pass §10.7 security gate
2. Add to config/mcp.example.json
3. Log in INSTALL_LOG.md
4. Wire to agent's handle_tool()

### New API Route
1. Add router in packages/api/src/hermes_api/routes/{name}.py
2. Include in main.py
3. Add request/response models to schemas.py
