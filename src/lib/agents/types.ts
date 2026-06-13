export const AGENT_IDS = ["claude-code", "openclaw", "hermes", "obsidian"] as const;

export type AgentId = (typeof AGENT_IDS)[number];
export type AgentState = "live" | "degraded" | "offline" | "mock";

export interface AgentHealth {
  id: AgentId;
  name: string;
  role: string;
  state: AgentState;
  detail: string;
  lastCheckedAt: string;
  source: "mock" | "local-adapter";
}

export interface AgentStatusResponse {
  mode: "mock" | "local";
  generatedAt: string;
  agents: AgentHealth[];
  warning?: string;
}
