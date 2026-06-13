# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| `main` | Yes, after a validated release |
| Open pull-request branches | Best effort during review |
| Historical branches | No |

## Reporting a vulnerability

Do not open a public issue for sensitive security reports.

Report privately via email: **oneflawlessstudio@gmail.com**

Include the affected commit or version, reproduction steps, observed impact and any relevant logs with secrets removed.

Response timing is best effort; no contractual service level is claimed.

## Current security scope

The current application is a local, read-only scaffold with deterministic mock agent data.

In scope:

- unintended exposure through dashboard or API responses;
- permission-policy bypasses;
- committed credentials or sensitive values;
- dependency vulnerabilities;
- unsafe defaults introduced by future adapter work.

Not currently implemented:

- real agent bridges;
- local process control;
- vault-content access;
- remote gateway exposure;
- external communications;
- billable API calls.

Upstream vulnerabilities in third-party agents or tools should also be reported to their respective maintainers.

## Current controls

- No credential is required by the scaffold.
- `.env*` secrets are excluded from version control.
- Secret scanning runs in GitHub Actions.
- Dependabot is configured for npm and GitHub Actions.
- Agent data is produced by a deterministic mock provider.
- Capability decisions are explicit and deny by default.
- Consequential capabilities require approval.
- Irreversible data capability is denied.
- Permission boundaries are covered by automated tests.

## Requirements for future adapters

Before enabling an adapter, add and validate:

- local trust boundary and authentication where applicable;
- least-privilege credentials;
- input and output validation;
- timeout, cancellation and safe failure;
- secret redaction;
- authorization and approval checks;
- audit events;
- normal, error and unauthorized-path tests;
- rollback or recovery procedures.
