export const RUNTIME_POLICY = {
  statusPanel: true,
  metadataPanel: true,
  contentAccess: false,
  adapterCalls: false,
  stateChanges: false,
  paidServices: false
} as const;

export type RuntimePolicy = typeof RUNTIME_POLICY;

export function enabledFeatures(policy: RuntimePolicy = RUNTIME_POLICY): string[] {
  return Object.entries(policy)
    .filter(([, enabled]) => enabled)
    .map(([name]) => name);
}
