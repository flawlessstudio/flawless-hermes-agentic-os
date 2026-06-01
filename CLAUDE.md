# Hermes Agent OS — Claude Code Configuration

## Project Context
This is a local-first Agent OS. The primary language is Python 3.12+ (backend/agents) and TypeScript (frontend/Mission Control).

## Branch
Always develop on `claude/busy-fermi-8Wnn2`.

## Architecture Decisions (frozen)
- Local-first; VPS is opt-in only
- No secrets ever in code, commits, or prompts
- Atomic writes: write-temp → fsync → rename
- Each agent has a ALLOWED_TOOLS frozenset — never bypass sandbox
- WCAG AA on all UI components

## Commands
- `make install` — install all dependencies
- `make dev` — start backend + frontend dev servers
- `make test` — run pytest + vitest
- `make lint` — ruff + mypy + eslint
- `make check` — full GATE (lint + test + security scan)

## Allowed Tools
- Read, Edit, Write, Bash (no destructive flags without confirmation)
- Git (no force-push to main)

## Workflow
1. Read SPEC.md before making architectural decisions
2. Run `make lint` before committing
3. Never write API keys or tokens — use PAUSA HUMANA protocol
4. All new MCP connectors must pass §10.7 security GATE
5. Register every installed item in INSTALL_LOG.md
