import { describe, expect, it } from "vitest";

import { RUNTIME_POLICY, enabledFeatures } from "../src/lib/policy/runtime";

describe("runtime policy", () => {
  it("enables only bounded observation features", () => {
    expect(enabledFeatures()).toEqual(["statusPanel", "metadataPanel"]);
  });

  it("keeps integrations and stateful features disabled", () => {
    expect(RUNTIME_POLICY.contentAccess).toBe(false);
    expect(RUNTIME_POLICY.adapterCalls).toBe(false);
    expect(RUNTIME_POLICY.stateChanges).toBe(false);
    expect(RUNTIME_POLICY.paidServices).toBe(false);
  });
});
