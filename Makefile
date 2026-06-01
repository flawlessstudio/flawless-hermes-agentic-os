.PHONY: install dev test lint build clean check format

# ──────────────────────────────────────────────
# Bootstrap
# ──────────────────────────────────────────────
install:
	@echo "→ Installing Python dependencies (uv)…"
	uv sync --all-packages
	@echo "→ Installing Node dependencies (pnpm)…"
	pnpm install
	@echo "✓ All dependencies installed"

# ──────────────────────────────────────────────
# Development servers
# ──────────────────────────────────────────────
dev:
	@echo "→ Starting API + frontend in parallel…"
	@trap 'kill 0' SIGINT; \
	  uv run uvicorn hermes_api.main:app --reload --port 8000 & \
	  pnpm --filter mission-control dev & \
	  wait

dev-api:
	uv run uvicorn hermes_api.main:app --reload --port 8000

dev-ui:
	pnpm --filter mission-control dev

# ──────────────────────────────────────────────
# Testing
# ──────────────────────────────────────────────
test:
	@echo "→ Running Python tests…"
	uv run pytest --cov=packages --cov-report=term-missing -q
	@echo "→ Running Vitest…"
	pnpm --filter mission-control test --run

test-py:
	uv run pytest --cov=packages --cov-report=term-missing -v

test-ui:
	pnpm --filter mission-control test --run

test-e2e:
	pnpm --filter mission-control exec playwright test

# ──────────────────────────────────────────────
# Linting / Formatting
# ──────────────────────────────────────────────
lint:
	@echo "→ Ruff check…"
	uv run ruff check packages agents
	@echo "→ Mypy check…"
	uv run mypy --package hermes_core --package hermes_memory --package hermes_orchestrator --package hermes_api
	@echo "→ ESLint…"
	pnpm --filter mission-control lint
	@echo "✓ All lint checks passed"

format:
	uv run ruff format packages agents
	uv run ruff check --fix packages agents
	pnpm --filter mission-control format

# ──────────────────────────────────────────────
# Build
# ──────────────────────────────────────────────
build:
	@echo "→ Building Python packages…"
	uv build --all-packages
	@echo "→ Building Next.js…"
	pnpm --filter mission-control build
	@echo "✓ Build complete"

# ──────────────────────────────────────────────
# Security
# ──────────────────────────────────────────────
security:
	@echo "→ Running semgrep…"
	semgrep --config=auto packages agents --error
	@echo "→ Running OSV dependency scan…"
	uv run pip list --format=json | python -m osv_scanner.main --json -

# ──────────────────────────────────────────────
# Aggregate gates
# ──────────────────────────────────────────────
check: lint test build
	@echo "✓ All gates passed"

# ──────────────────────────────────────────────
# Clean
# ──────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name dist -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .next -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
	@echo "✓ Clean complete"
