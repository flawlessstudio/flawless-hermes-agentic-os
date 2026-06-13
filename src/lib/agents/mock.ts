import type { AgentStatusResponse } from "./types";

export function getMockAgentStatus(now = new Date()): AgentStatusResponse {
  const lastCheckedAt = now.toISOString();

  return {
    mode: "mock",
    generatedAt: lastCheckedAt,
    warning: "Mock status only. No local agent process, gateway, vault or paid API is contacted.",
    agents: [
      {
        id: "claude-code",
        name: "Claude Code",
        role: "Intelligence and implementation",
        state: "mock",
        detail: "Adapter disabled until credentials and approval policy are configured.",
        lastCheckedAt,
        source: "mock"
      },
      {
        id: "openclaw",
        name: "OpenClaw",
        role: "Local gateway and session routing",
        state: "mock",
        detail: "Gateway probing is not enabled in the validated scaffold.",
        lastCheckedAt,
        source: "mock"
      },
      {
        id: "hermes",
        name: "Hermes Agent",
        role: "Execution layer",
        state: "mock",
        detail: "Tool execution is denied by default and not connected.",
        lastCheckedAt,
        source: "mock"
      },
      {
        id: "obsidian",
        name: "Obsidian Vault",
        role: "Local memory layer",
        state: "mock",
        detail: "No filesystem or vault access is performed.",
        lastCheckedAt,
        source: "mock"
      }
    ]
  };
}
