# Permission and Approval Policy

## Policy model

The scaffold uses an explicit, deny-by-default capability registry implemented in:

```text
src/lib/policy/permissions.ts
```

Every declared capability has one decision:

```text
allow
approval-required
deny
```

Any capability absent from the registry resolves to `deny`.

## Current decisions

| Capability family | Decision | Boundary |
|---|---|---|
| Read-only health status | Allow | Mock or reviewed local status only |
| Non-sensitive metadata | Allow | No content or secrets |
| Vault access | Approval required | Target and purpose must be explicit |
| Tool invocation | Approval required | Scoped, observable and cancellable |
| Dependency or system changes | Approval required | Reviewed impact and recovery plan |
| Repository writes | Approval required | Reviewed diff and explicit authorization |
| External communication | Approval required | Recipient and content approval |
| Billable services | Approval required | Approved budget and limit |
| Irreversible data capability | Deny | Not available in the scaffold |

## Approval record requirements

A future approval mechanism must record:

```text
request ID
actor
capability
purpose
target
parameters
expected effect
risk
cost exposure
expiration
decision
decision owner
timestamp
result
```

## Mandatory safeguards for future adapters

- least privilege;
- explicit allowlists;
- scoped credentials;
- input and output validation;
- timeout and cancellation;
- idempotency where relevant;
- preview before mutation;
- rollback or recovery;
- audit events;
- safe failure;
- local binding and authentication where a gateway is introduced.

## Current enforcement evidence

`tests/permissions.test.ts` verifies:

- one rule per capability;
- irreversible data capability is denied;
- consequential capabilities require approval;
- only bounded read-only capabilities are allowed directly.
