export const CAPABILITIES = [
  "status.read",
  "metadata.read",
  "vault.read",
  "vault.write",
  "tool.invoke",
  "dependency.change",
  "system.change",
  "repository.write",
  "communication.external",
  "billing.consume",
  "data.irreversible"
] as const;

export type Capability = (typeof CAPABILITIES)[number];
export type PolicyDecision = "allow" | "deny" | "approval-required";

export interface PolicyRule {
  capability: Capability;
  decision: PolicyDecision;
  rationale: string;
}

export const POLICY_RULES: readonly PolicyRule[] = [
  { capability: "status.read", decision: "allow", rationale: "Read-only health information." },
  { capability: "metadata.read", decision: "allow", rationale: "Non-sensitive local metadata only." },
  { capability: "vault.read", decision: "approval-required", rationale: "Content may be sensitive." },
  { capability: "vault.write", decision: "approval-required", rationale: "Requires preview and recovery." },
  { capability: "tool.invoke", decision: "approval-required", rationale: "Must be scoped and observable." },
  { capability: "dependency.change", decision: "approval-required", rationale: "Changes supply-chain exposure." },
  { capability: "system.change", decision: "approval-required", rationale: "May affect security and recovery." },
  { capability: "repository.write", decision: "approval-required", rationale: "Requires reviewed changes." },
  { capability: "communication.external", decision: "approval-required", rationale: "Creates external consequences." },
  { capability: "billing.consume", decision: "approval-required", rationale: "Requires an approved budget." },
  { capability: "data.irreversible", decision: "deny", rationale: "Disabled in the scaffold." }
] as const;

export function getPolicyDecision(capability: Capability): PolicyDecision {
  return POLICY_RULES.find((rule) => rule.capability === capability)?.decision ?? "deny";
}

export function isAllowedWithoutApproval(capability: Capability): boolean {
  return getPolicyDecision(capability) === "allow";
}
