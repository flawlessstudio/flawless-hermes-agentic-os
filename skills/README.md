# Skills Registry — Hermes Agent OS

Skills are composable instruction sets (SKILL.md files) that extend agent capabilities.
Each skill is mapped to one or more phases and passes the §10.7 Security GATE before activation.

## Structure

```
skills/
├── README.md          # This file — registry index
├── code-review/
│   └── SKILL.md
├── testing/
│   └── SKILL.md
├── security/
│   └── SKILL.md
└── research/
    └── SKILL.md
```

## Security GATE (§10.7)

Before any skill is activated:

1. License is OSS and permissive
2. No secrets or credentials embedded
3. No exfiltration of data to external services without explicit config
4. Semgrep scan passes
5. Source repository is public and maintained
6. Registered in `INSTALL_LOG.md`

## Phase Mapping

| Skill | Phases | Source |
|-------|--------|--------|
| code-review | F0, F5, F9 | community |
| testing/TDD | F0, F5, F7 | community |
| security-hardening | F9 | community |
| research/synthesis | F2, F4 | community |
| design-tokens/a11y | F6, F8 | community |
| documentation | F11 | community |

## Adding a Skill

```bash
# 1. Create the skill directory
mkdir -p skills/<name>

# 2. Write SKILL.md with: purpose, usage, phase, gate status
# 3. Register in INSTALL_LOG.md
# 4. Run security gate: make check-skill SKILL=<name>
```
