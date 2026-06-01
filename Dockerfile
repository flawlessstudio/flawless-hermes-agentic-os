# syntax=docker/dockerfile:1.7
# ─────────────────────────────────────────────────────────────
# Stage 1: Python deps (build-time only)
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS python-builder

WORKDIR /build

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency manifests first (layer cache)
COPY pyproject.toml uv.lock ./
COPY packages/ packages/
COPY agents/ agents/

# Install into a venv at /build/.venv
RUN uv sync --frozen --no-dev

# ─────────────────────────────────────────────────────────────
# Stage 2: Node deps (build-time only)
# ─────────────────────────────────────────────────────────────
FROM node:22-slim AS node-builder

WORKDIR /build

RUN corepack enable && corepack prepare pnpm@latest --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/ apps/

RUN pnpm install --frozen-lockfile
RUN pnpm --filter mission-control build

# ─────────────────────────────────────────────────────────────
# Stage 3: Runtime image
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="Hermes Agent OS"
LABEL org.opencontainers.image.description="Local-first agentic OS — API + Mission Control"
LABEL org.opencontainers.image.source="https://github.com/flawlessstudio/flawless-hermes-agentic-os"

WORKDIR /app

# Install Node runtime for serving the Next.js app
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python venv from builder
COPY --from=python-builder /build/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application source
COPY packages/ packages/
COPY agents/ agents/
COPY config/ config/

# Copy compiled Next.js app
COPY --from=node-builder /build/apps/mission-control/.next ./apps/mission-control/.next
COPY --from=node-builder /build/apps/mission-control/public ./apps/mission-control/public
COPY --from=node-builder /build/apps/mission-control/package.json ./apps/mission-control/
COPY --from=node-builder /build/node_modules ./node_modules

# Non-root user
RUN useradd --uid 1001 --no-create-home --shell /bin/false hermes
USER hermes

# API port
EXPOSE 8000
# Mission Control port
EXPOSE 3000

# Health-check against the FastAPI /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default: run the FastAPI backend.  Override CMD for the UI process.
CMD ["python", "-m", "uvicorn", "hermes_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
