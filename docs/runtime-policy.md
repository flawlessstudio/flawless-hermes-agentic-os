# Runtime Feature Policy

The executable policy is defined in:

```text
src/lib/policy/runtime.ts
```

## Current state

| Feature | Enabled | Boundary |
|---|:---:|---|
| Status panel | Yes | Deterministic mock status |
| Metadata panel | Yes | Non-sensitive metadata |
| Content access | No | Not implemented |
| Adapter calls | No | Not implemented |
| State changes | No | Not implemented |
| Paid services | No | Not implemented |

Unknown or future capabilities are not enabled implicitly.

## Test evidence

`tests/runtime-policy.test.ts` verifies that only the two observation features are enabled and all integration or stateful features remain disabled.

## Entry criteria for expanding the policy

A feature may be enabled only after:

1. purpose and scope are approved;
2. risk and data exposure are documented;
3. implementation is bounded;
4. validation covers normal and failure paths;
5. recovery is defined where relevant;
6. CI passes against the changed policy and implementation.
