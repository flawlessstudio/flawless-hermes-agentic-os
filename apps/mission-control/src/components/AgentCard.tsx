"use client";

import { type AgentInfo } from "@/lib/api";
import { formatRelativeTime } from "@/lib/utils";

const STATUS_COLORS: Record<AgentInfo["status"], string> = {
  idle: "var(--color-text-muted)",
  running: "var(--color-success)",
  error: "var(--color-error)",
  paused: "var(--color-warning)",
};

interface AgentCardProps {
  agent: AgentInfo;
}

export function AgentCard({ agent }: AgentCardProps) {
  const statusColor = STATUS_COLORS[agent.status];

  return (
    <article
      className="rounded-xl p-5 border flex flex-col gap-3"
      style={{
        background: "var(--color-surface-2)",
        borderColor: "var(--color-border)",
      }}
      aria-label={`Agent ${agent.id}, status: ${agent.status}`}
    >
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-base">{agent.id}</h3>
        <div
          className="flex items-center gap-1.5"
          aria-label={`Status: ${agent.status}`}
        >
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: statusColor }}
            aria-hidden="true"
          />
          <span
            className="text-xs capitalize"
            style={{ color: statusColor }}
          >
            {agent.status}
          </span>
        </div>
      </div>
      <div className="flex flex-wrap gap-1" role="list" aria-label="Allowed tools">
        {agent.allowed_tools.slice(0, 4).map((tool) => (
          <span
            key={tool}
            role="listitem"
            className="text-xs px-2 py-0.5 rounded"
            style={{
              background: "var(--color-surface)",
              color: "var(--color-text-muted)",
            }}
          >
            {tool}
          </span>
        ))}
        {agent.allowed_tools.length > 4 && (
          <span
            className="text-xs px-2 py-0.5 rounded"
            style={{
              background: "var(--color-surface)",
              color: "var(--color-text-muted)",
            }}
          >
            +{agent.allowed_tools.length - 4} more
          </span>
        )}
      </div>
      <div
        className="flex justify-between text-xs"
        style={{ color: "var(--color-text-muted)" }}
      >
        <span>{agent.message_count} messages</span>
        {agent.last_active != null && (
          <span>{formatRelativeTime(agent.last_active)}</span>
        )}
      </div>
    </article>
  );
}
