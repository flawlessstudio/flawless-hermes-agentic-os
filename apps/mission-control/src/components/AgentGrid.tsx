"use client";

import { useAgents } from "@/hooks/useAgents";
import { AgentCard } from "./AgentCard";
import { AgentCardSkeleton } from "./Skeleton";

export function AgentGrid() {
  const { agents, loading, error } = useAgents();

  if (loading) {
    return (
      <section aria-label="Agents loading" aria-busy="true">
        <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <AgentCardSkeleton key={i} />
          ))}
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        className="rounded-xl p-5 border"
        style={{
          background: "var(--color-surface-2)",
          borderColor: "var(--color-error)",
        }}
      >
        <p className="font-medium" style={{ color: "var(--color-error)" }}>
          Failed to load agents
        </p>
        <p className="text-sm mt-1" style={{ color: "var(--color-text-muted)" }}>
          {error}
        </p>
      </div>
    );
  }

  if (agents.length === 0) {
    return (
      <div
        className="rounded-xl p-10 border text-center"
        style={{
          background: "var(--color-surface-2)",
          borderColor: "var(--color-border)",
        }}
      >
        <p style={{ color: "var(--color-text-muted)" }}>
          No agents registered yet.
        </p>
      </div>
    );
  }

  return (
    <section aria-label="Active agents">
      <div
        className="grid gap-4"
        style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}
      >
        {agents.map((agent) => (
          <AgentCard key={agent.id} agent={agent} />
        ))}
      </div>
    </section>
  );
}
