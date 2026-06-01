# Hermes Agent OS — Operational Runbook

## Prerequisites

### System Requirements
- Python 3.12+
- Node.js 22+ with pnpm
- uv (Python package manager)
- Git
- SQLite 3.35+ (for WAL mode)

### Installation

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install pnpm
curl -fsSL https://get.pnpm.io/install.sh | sh -

# Clone repo
git clone <repo-url> flawless-hermes-agentic-os
cd flawless-hermes-agentic-os
git checkout claude/busy-fermi-8Wnn2

# Install all dependencies
make install
```

## Starting Services

### Development Mode (all services)
```bash
make dev
# Starts:
#   - FastAPI backend on http://localhost:8000
#   - Next.js frontend on http://localhost:3000
```

### Individual Services
```bash
# Backend only
make dev-api    # uvicorn with --reload

# Frontend only
make dev-ui     # next dev
```

## Health Verification

```bash
# Check backend health
curl http://localhost:8000/health
# Expected: {"status":"ok","version":"0.1.0","ts":...,"components":{...}}

# Check readiness
curl http://localhost:8000/ready
# Expected: {"ready":true}

# Check frontend
open http://localhost:3000
# Expected: Mission Control dashboard loads
```

## Running Tests

```bash
# All tests
make test

# Python only
make test-py

# Frontend only
make test-ui

# E2E (requires running services)
make test-e2e
```

## Running Lint

```bash
# All linters
make lint

# Auto-fix
make format
```

## Full Gate Check

```bash
make check
# Runs: lint → test → build
# All must pass before merging to main
```

## Common Issues and Fixes

### Issue: ChromaDB import error
```
ModuleNotFoundError: No module named 'chromadb'
```
**Fix**: Run `uv sync --all-packages`

### Issue: SQLite WAL not available
```
sqlite3.OperationalError: cannot change into wal journal mode
```
**Fix**: Ensure SQLite 3.7.0+ is installed: `sqlite3 --version`

### Issue: Port 8000 already in use
```
[Errno 98] Address already in use
```
**Fix**: `lsof -ti:8000 | xargs kill -9`

### Issue: Next.js build fails with type errors
```
Type error: Property 'X' does not exist on type 'Y'
```
**Fix**: Run `pnpm tsc --noEmit` in apps/mission-control/ to see full errors

### Issue: FileLock timeout
```
hermes_core.exceptions.LockTimeoutError: Could not acquire lock...
```
**Fix**: Check for stale lock file: `ls packages/*/data/*.lock` and delete if process is dead

### Issue: ChromaDB persistence directory permissions
```
PermissionError: [Errno 13] Permission denied: './data/memory/vector'
```
**Fix**: `mkdir -p data/memory/vector && chmod 755 data/memory/vector`

## Backup and Restore

### Backup AtomicStore
The store automatically creates a `.bak` file before every write. For manual backup:
```bash
cp data/state.db data/state.db.$(date +%Y%m%d_%H%M%S).bak
```

### Restore from Backup
```python
from hermes_core import AtomicStore
store = AtomicStore("data/state.db")
recovered = store.recover()
print(f"Recovered: {recovered}")
```

### Backup ChromaDB Memory
```bash
tar -czf memory_backup_$(date +%Y%m%d).tar.gz data/memory/
```

### Restore ChromaDB Memory
```bash
tar -xzf memory_backup_20260601.tar.gz -C ./
```

## Adding a New Agent

1. Create the agent file:
```bash
mkdir -p agents/{name}
cat > agents/{name}/agent.py << 'PYEOF'
from hermes_orchestrator.agent import BaseAgent
from hermes_orchestrator.schemas import AgentConfig, ToolCall, ToolResult

class MyAgent(BaseAgent):
    ALLOWED_TOOLS: frozenset[str] = frozenset({"tool_one", "tool_two"})

    async def handle_tool(self, call: ToolCall) -> ToolResult:
        # Implement tool handling
        ...
PYEOF
```

2. Register at startup in packages/api/src/hermes_api/main.py lifespan

3. Add any MCP tools to config/mcp.example.json (pass §10.7 gate)

4. Update INSTALL_LOG.md

5. Add tests in agents/{name}/tests/

## Adding a New MCP Connector

### §10.7 Security Gate Checklist

```
[ ] Source verified (GitHub org/repo identified)
[ ] License compatible (MIT, Apache-2.0, LGPL-2.1+)
[ ] Secrets via environment only (no tokens in config)
[ ] Tier assigned (0=official, 1=community, 2=experimental)
[ ] INSTALL_LOG.md entry populated
[ ] mcp.example.json entry added with all metadata fields
[ ] PAUSA_HUMANA flag set if credentials required
```

### Adding to config
Edit `config/mcp.example.json`:
```json
"my-connector": {
  "command": "npx",
  "args": ["-y", "my-mcp-server"],
  "env": {
    "MY_API_KEY": "<PAUSA_HUMANA: set in environment>"
  },
  "_tier": 1,
  "_source": "org/my-mcp-server",
  "_license": "MIT",
  "_requires_human_pause": true
}
```

### Adding to INSTALL_LOG.md
```markdown
| my-mcp-server | MCP | 1 | 7.0 | org/my-mcp-server | MIT | 2026-06-01 | ✅ Approved |
```

## Rollback Procedures

### Rollback to Last Good Checkpoint
```python
from hermes_core import AtomicStore, CheckpointManager

store = AtomicStore("data/state.db")
mgr = CheckpointManager(store)
last = mgr.last_good()
print(f"Last good phase: {last.phase} at {last.ts}")
```

### Rollback Database
```bash
# Restore from automatic backup
cp data/state.bak data/state.db

# Or from manual backup
cp data/state.db.20260601_120000.bak data/state.db
```

### Rollback Git
```bash
# View recent commits
git log --oneline -20

# Revert to specific commit (creates new commit)
git revert <commit-hash>

# NEVER force-push to main
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| ANTHROPIC_API_KEY | Yes (for agents) | — | Claude API key |
| HERMES_DATA_DIR | No | ./data | Data directory |
| HERMES_LOG_LEVEL | No | INFO | Log level |
| HERMES_JSON_LOGS | No | false | JSON log format |
| NEXT_PUBLIC_API_URL | No | http://localhost:8000 | API base URL |

## Emergency Procedures

### Service Unresponsive
```bash
# Kill and restart
lsof -ti:8000 | xargs kill -9
make dev-api

# Check logs
tail -f /tmp/hermes-api.log
```

### Memory Store Corrupted
```bash
# Attempt automatic recovery
python -c "
from hermes_core import AtomicStore
s = AtomicStore('data/state.db')
ok = s.recover()
print('Recovered:', ok)
"

# If recovery fails, restore from backup
cp data/state.bak data/state.db
```

### Agent Stuck/Looping
```bash
# Kill the agent process (ops agent will auto-escalate)
# Then check activity feed in Mission Control for error events
# Review logs for SandboxViolation or tool timeout errors
```
