# Flawless Hermes — Agent OS

A production-grade, local-first Agent Operating System with Mission Control dashboard, specialized agents, persistent memory, and full MCP/Skills ecosystem.

## Architecture

- **Backend**: Python 3.12+, FastAPI, uv
- **Frontend**: Next.js 15, React 19, TypeScript strict, Tailwind CSS 4
- **State**: SQLite WAL, atomic writes, file-lock, git versioning
- **Memory**: ChromaDB (vector/RAG) + SQLite (graph) — local-first
- **Agents**: Claude API (claude-sonnet-4-6) with tool_use + sandbox
- **Observability**: structlog + OpenTelemetry
- **Security**: zero secrets in code, Semgrep CI, OSV audit

## Quick Start

```bash
make install   # install all deps
make dev       # start all services
make test      # run all tests
make check     # run all GATE checks
```

## Phases

| Phase | Description | Status |
|-------|-------------|--------|
| F0 | Bootstrap | ✅ |
| F1 | Atomic State Store | ✅ |
| F2 | Persistent Memory | ✅ |
| F3 | Agent Orchestrator | ✅ |
| F4 | Skills/MCP | ✅ |
| F5 | Backend API | ✅ |
| F6 | Mission Control UI | ✅ |
| F7 | UX/Flows | ✅ |
| F8 | Branding | ✅ |
| F9 | Security/Hardening | ✅ |
| F10 | Observability | ✅ |
| F11 | Packaging/Delivery | ✅ |

## Documentation

- [Architecture](docs/architecture.md)
- [Runbook](docs/runbook.md)
- [SPEC](SPEC.md)
- [Install Log](INSTALL_LOG.md)
