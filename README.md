# 🧠 Flawless Hermes Agentic OS

> **Local-first AI Operating System** — Mission Control dashboard for orchestrating Hermes Agent, OpenClaw and Claude Code as a unified agentic stack.

[![CI](https://github.com/flawlessstudio/flawless-hermes-agentic-os/actions/workflows/ci.yml/badge.svg)](https://github.com/flawlessstudio/flawless-hermes-agentic-os/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE.md)
[![Node](https://img.shields.io/badge/node-%3E%3D22.19-brightgreen)](https://nodejs.org)
[![Stack](https://img.shields.io/badge/stack-Next.js%20%7C%20Tailwind%20%7C%20Framer-black)](#stack)

---

## Overview

**Flawless Hermes Agentic OS** is a local Mission Control dashboard that connects and visualises the live status of your AI agents in a browser-based interface. No cloud dependency. No SaaS. Runs entirely on your machine.

Built on top of the validated [Hermes Agentic OS guide](https://skool.com/ai-profit-lab-7462) (AI Profit Boardroom) with a production-grade Flawless Studio architecture layer on top.

---

## Architecture

```
┌─────────────────────────────────────────┐
│              YOU (Mission Operator)     │
│          localhost:3000 · browser       │
└────────────────┬────────────────────────┘
                 │
     ┌───────────▼───────────┐
     │  Next.js Dashboard    │  ← Mission Control UI
     │  Tailwind + Framer    │
     └──┬─────────┬──────────┘
        │         │
┌───────▼──┐  ┌───▼──────┐
│  Claude  │  │ OpenClaw │  ← Intelligence + Gateway
│  Code    │  │ Gateway  │
└──────────┘  └────┬─────┘
                   │
            ┌──────▼──────┐
            │   Hermes    │  ← Execution Layer
            │   Agent     │
            └──────┬──────┘
                   │
            ┌──────▼──────┐
            │   Obsidian  │  ← Self / Memory Layer
            │   Vault     │
            └─────────────┘
```

| Layer | Tool | Role |
|---|---|---|
| Intelligence | Claude Code | Think, plan, build |
| Gateway | OpenClaw | Route, coordinate, manage sessions |
| Execution | Hermes Agent | Research, kanban, plugins, tool calls |
| Self | Obsidian | Goals, journal, permanent memory |

---

## Stack

| Area | Technology |
|---|---|
| Dashboard | Next.js 15, React 19, TypeScript |
| Styling | Tailwind CSS v4, Framer Motion |
| Runtime | Node.js 24 LTS |
| Agent Layer | Hermes Agent v0.15+, OpenClaw v2026 |
| Intelligence | Claude Code (Anthropic API) |
| Memory | Obsidian (local vault) |

---

## Prerequisites

| Requirement | Minimum | Recommended |
|---|---|---|
| RAM | 8 GB | 16 GB |
| Disk | 5 GB free | 20 GB |
| OS | macOS 13 · Ubuntu 22.04 · Windows 11 WSL2 | macOS 14 · Ubuntu 24.04 |
| Node.js | v22.19 | v24 LTS |
| Browser | Chrome 120 / Safari 17 | Chrome (voice input) |

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/flawlessstudio/flawless-hermes-agentic-os.git
cd flawless-hermes-agentic-os

# 2. Install Node 24 LTS (if not present)
nvm install 24 && nvm use 24

# 3. Install Hermes Agent
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# 4. Install OpenClaw
npm install -g openclaw@latest
openclaw onboard --install-daemon

# 5. Install project dependencies
npm install

# 6. Copy env and add your API key
cp .env.example .env.local
# → Edit .env.local and add ANTHROPIC_API_KEY

# 7. Verify all agents are live
openclaw gateway status   # → should show LIVE
hermes --version          # → should respond
openclaw doctor           # → should pass clean

# 8. Launch dashboard
npm run dev
# → open http://localhost:3000
```

---

## Environment Variables

See [`.env.example`](.env.example) for all variables. Never commit real values.

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | Claude Code API key (pay-per-token) |
| `OBSIDIAN_VAULT_PATH` | ✅ | Absolute path to your Obsidian vault |
| `OPENCLAW_GATEWAY_PORT` | ⬜ | Default: `4242` |
| `HERMES_PORT` | ⬜ | Default: `7777` |

---

## Cost Notice

> ⚠️ **Claude Code is NOT free.** It requires an Anthropic account with active billing.
> - Pro plan: $20/month (Sonnet)
> - Max plan: $100–200/month (Opus)
> - API pay-per-token: from $1/M tokens (Haiku) to $25/M tokens (Opus)
>
> The local dashboard and agents (Hermes, OpenClaw, Obsidian) are free. Only Claude Code has a cost.

---

## OS-Specific Notes

**Obsidian vault path by OS:**

```bash
# macOS
~/Documents/Obsidian Vault

# Linux
~/ObsidianVault

# Windows WSL2
/mnt/c/Users/<username>/Documents/ObsidianVault

# Windows native
C:\Users\<username>\Documents\ObsidianVault
```

**OpenClaw DEGRADED fix:**
```bash
openclaw doctor
openclaw gateway restart
# or simply:
openclaw update
```

---

## Scripts

```bash
npm run dev          # Start development server
npm run build        # Production build
npm run start        # Start production server
npm run lint         # ESLint check
npm run lint:fix     # ESLint auto-fix
npm run type-check   # TypeScript check
```

---

## Project Structure

```
flawless-hermes-agentic-os/
├── .github/
│   ├── workflows/          # CI, secret-scan
│   ├── ISSUE_TEMPLATE/     # Bug, feature templates
│   └── PULL_REQUEST_TEMPLATE.md
├── src/
│   ├── app/                # Next.js App Router
│   ├── components/         # UI components
│   ├── lib/                # Agent bridge utilities
│   └── types/              # TypeScript types
├── public/
├── .env.example
├── .nvmrc
├── .editorconfig
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
└── README.md
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Security

See [SECURITY.md](SECURITY.md). Never push API keys. Secret scanning is active in CI.

---

## License

MIT © 2026 [Flawless Studio](https://github.com/flawlessstudio)
