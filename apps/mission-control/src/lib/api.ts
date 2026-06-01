const API_BASE =
  typeof process !== "undefined"
    ? (process.env["NEXT_PUBLIC_API_URL"] ?? "http://localhost:8000")
    : "http://localhost:8000";

export interface AgentInfo {
  id: string;
  status: "idle" | "running" | "error" | "paused";
  allowed_tools: string[];
  message_count: number;
  last_active: number | null;
}

export interface MemoryResult {
  id: string;
  content: string;
  score: number;
  agent_id: string;
  ts: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  ts: number;
  components: Record<string, string>;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API error ${res.status}: ${error}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => apiFetch<HealthResponse>("/health"),
  agents: {
    list: () => apiFetch<AgentInfo[]>("/agents/"),
    get: (id: string) => apiFetch<AgentInfo>(`/agents/${id}`),
  },
  memory: {
    query: (query: string, agentId = "global", topK = 5) =>
      apiFetch<MemoryResult[]>("/memory/query", {
        method: "POST",
        body: JSON.stringify({ query, agent_id: agentId, top_k: topK }),
      }),
    store: (
      content: string,
      agentId = "global",
      metadata: Record<string, unknown> = {}
    ) =>
      apiFetch<{ id: string; stored: boolean }>("/memory/store", {
        method: "POST",
        body: JSON.stringify({ content, agent_id: agentId, metadata }),
      }),
  },
};
