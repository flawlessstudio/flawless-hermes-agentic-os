"use client";

import { useState, useEffect, useCallback } from "react";
import { api, type AgentInfo, type HealthResponse } from "@/lib/api";

/** Re-export AgentInfo as Agent for component convenience */
export type { AgentInfo as Agent };

export function useAgents(pollInterval = 5000): {
  agents: AgentInfo[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
} {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAgents = useCallback(async () => {
    try {
      const data = await api.agents.list();
      setAgents(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch agents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAgents();
    const interval = setInterval(() => void fetchAgents(), pollInterval);
    return () => clearInterval(interval);
  }, [fetchAgents, pollInterval]);

  return { agents, loading, error, refetch: fetchAgents };
}

export function useSSE(url = "http://localhost:8000/stream/events"): {
  lastEvent: unknown;
  connected: boolean;
} {
  const [lastEvent, setLastEvent] = useState<unknown>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const es = new EventSource(url);
    es.onopen = () => setConnected(true);
    es.onmessage = (e: MessageEvent<string>) => {
      try {
        setLastEvent(JSON.parse(e.data));
      } catch {
        // non-JSON event — ignore
      }
    };
    es.onerror = () => setConnected(false);
    return () => es.close();
  }, [url]);

  return { lastEvent, connected };
}

/**
 * useHealth — polls /health every 30 s and returns system health.
 *
 * Components that import this expect `{ health, error }`.
 */
export function useHealth(pollInterval = 30_000): {
  health: HealthResponse | null;
  error: string | null;
} {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      const h = await api.health();
      setHealth(h);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Health check failed");
      setHealth(null);
    }
  }, []);

  useEffect(() => {
    void fetchHealth();
    const id = setInterval(() => void fetchHealth(), pollInterval);
    return () => clearInterval(id);
  }, [fetchHealth, pollInterval]);

  return { health, error };
}
