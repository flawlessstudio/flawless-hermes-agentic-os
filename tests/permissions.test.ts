import { describe, expect, it } from "vitest";

import {
  CAPABILITIES,
  POLICY_RULES,
  getPolicyDecision,
  isAllowedWithoutApproval
} from "../src/lib/policy/permissions";

describe("permission policy", () => {
  it("defines exactly one rule for every capability", () => {
    expect(POLICY_RULES).toHaveLength(CAPABILITIES.length);
    expect(new Set(POLICY_RULES.map((rule) => rule.capability)).size).toBe(CAPABILITIES.length);
  });

  it("denies irreversible data capability", () => {
    expect(getPolicyDecision("data.irreversible")).toBe("deny");
    expect(isAllowedWithoutApproval("data.irreversible")).toBe(false);
  });

  it("requires approval for consequential capabilities", () => {
    expect(getPolicyDecision("tool.invoke")).toBe("approval-required");
    expect(getPolicyDecision("repository.write")).toBe("approval-required");
    expect(getPolicyDecision("communication.external")).toBe("approval-required");
    expect(getPolicyDecision("billing.consume")).toBe("approval-required");
  });

  it("allows only bounded read-only capabilities", () => {
    expect(CAPABILITIES.filter(isAllowedWithoutApproval)).toEqual(["status.read", "metadata.read"]);
  });
});
