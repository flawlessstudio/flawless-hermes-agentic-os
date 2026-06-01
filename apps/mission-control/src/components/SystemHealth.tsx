"use client";

import { useHealth } from "@/hooks/useAgents";

const COMPONENT_ICONS: Record<string, string> = {
  store: "⬡",
  memory: "◈",
  orchestrator: "⬟",
  api: "◇",
};

export function SystemHealth() {
  const { health, error } = useHealth();

  if (error) {
    return (
      <div
        role="alert"
        className="rounded-xl px-5 py-3 border text-sm flex items-center gap-3"
        style={{
          background: "var(--color-error-subtle)",
          borderColor: "var(--color-error)",
          color: "var(--color-error)",
        }}
      >
        <span aria-hidden="true">⚠</span>
        API unreachable — check that the backend is running on port 8000.
      </div>
    );
  }

  if (!health) {
    return (
      <div
        aria-busy="true"
        aria-label="Loading system health"
        className="rounded-xl px-5 py-3 border h-12 animate-pulse"
        style={{
          background: "var(--color-surface-2)",
          borderColor: "var(--color-border)",
        }}
      />
    );
  }

  const components = Object.entries(health.components);

  return (
    <div
      className="rounded-xl border px-5 py-3 flex items-center gap-6 overflow-x-auto"
      style={{
        background: "var(--color-surface-2)",
        borderColor: "var(--color-border)",
      }}
      role="status"
      aria-label="System component health"
    >
      <span
        className="text-xs font-medium shrink-0"
        style={{ color: "var(--color-text-muted)" }}
      >
        Components
      </span>
      <div className="flex items-center gap-4 flex-wrap">
        {components.map(([name, status]) => (
          <div key={name} className="flex items-center gap-1.5">
            <span
              aria-hidden="true"
              className="text-sm"
              style={{
                color:
                  status === "ok"
                    ? "var(--color-success)"
                    : "var(--color-error)",
              }}
            >
              {COMPONENT_ICONS[name] ?? "◦"}
            </span>
            <span
              className="text-xs capitalize"
              style={{ color: "var(--color-text-muted)" }}
              aria-label={`${name}: ${status}`}
            >
              {name}
            </span>
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{
                background:
                  status === "ok"
                    ? "var(--color-success)"
                    : "var(--color-error)",
              }}
              aria-hidden="true"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
