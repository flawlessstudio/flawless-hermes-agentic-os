# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| `main` (latest) | ✅ |
| Older branches | ❌ |

## Reporting a Vulnerability

Do **not** open a public issue for security vulnerabilities.

Report privately via email: **oneflawlessstudio@gmail.com**

- Subject: `[SECURITY] flawless-hermes-agentic-os — <short description>`
- Include: steps to reproduce, impact assessment, affected version
- SLA: acknowledgement within **48 hours**, patch timeline communicated within **7 days**

## Scope

**In scope:**
- Injection vulnerabilities in agent bridge layer
- Secret/credential exposure via logs or API responses
- Unauthorized local access via dashboard endpoints
- Dependency vulnerabilities (high/critical CVEs)

**Out of scope:**
- Vulnerabilities in Hermes Agent, OpenClaw or Claude Code upstream projects
- Social engineering
- Physical access attacks

## Security Practices

- Zero secrets in code or Git history
- All secrets via `.env.local` (gitignored)
- Secret scanning active in CI (see `.github/workflows/secret-scan.yml`)
- Dependabot enabled for npm dependencies
- Input validation on all agent bridge calls
- No PII logged
