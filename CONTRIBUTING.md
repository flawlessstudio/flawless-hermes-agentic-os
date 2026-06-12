# Contributing to Flawless Hermes Agentic OS

Thank you for your interest. This is a Flawless Studio project. Contributions are welcome via pull request.

## Setup

```bash
git clone https://github.com/flawlessstudio/flawless-hermes-agentic-os.git
cd flawless-hermes-agentic-os
nvm use
npm install
cp .env.example .env.local
```

## Branch Strategy

| Branch | Purpose |
|---|---|
| `main` | Stable, protected |
| `feat/<name>` | New features |
| `fix/<name>` | Bug fixes |
| `chore/<name>` | Maintenance, deps, config |

## Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add hermes live status widget
fix: correct openclaw gateway restart command
chore: update dependabot config
docs: add WSL2 obsidian path note
```

## Pull Request Checklist

- [ ] Branch from `main`, not a hotfix directly
- [ ] No secrets, API keys or `.env.local` committed
- [ ] `npm run lint` passes
- [ ] `npm run type-check` passes
- [ ] CHANGELOG.md updated under `[Unreleased]`
- [ ] PR description explains the change and why

## Prompt Change Protocol

If you change any agent prompt or bridge configuration:
- Document the change in the PR description
- Note which agent is affected (Hermes / OpenClaw / Claude)
- Include expected vs actual behaviour

## Questions

Open a [GitHub Discussion](https://github.com/flawlessstudio/flawless-hermes-agentic-os/discussions) or contact via [SECURITY.md](SECURITY.md) for sensitive topics.
