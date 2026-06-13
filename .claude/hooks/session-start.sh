#!/bin/bash
set -euo pipefail

# Only run in remote Claude Code on the web sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"

# ── Python dependencies ─────────────────────────────────────────────────────
echo "[session-start] Installing Python deps (uv sync)…"
uv sync --all-packages

# ── Node / pnpm dependencies ────────────────────────────────────────────────
echo "[session-start] Installing Node deps (pnpm install)…"
corepack enable
pnpm install --config.confirmModulesPurge=false

echo "[session-start] Done."
