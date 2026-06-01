"use client";

import { useSSE } from "@/hooks/useAgents";

export function StatusBar() {
  const { connected } = useSSE();

  return (
    <header
      className="flex items-center justify-between px-6 py-3 border-b"
      style={{
        borderColor: "var(--color-border)",
        background: "var(--color-surface)",
      }}
      role="banner"
    >
      <div className="flex items-center gap-3">
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold"
          style={{ background: "var(--color-accent)", color: "white" }}
          aria-hidden="true"
        >
          H
        </div>
        <span className="font-semibold tracking-tight">Hermes Agent OS</span>
      </div>
      <div
        className="flex items-center gap-2"
        aria-live="polite"
        aria-label="Connection status"
      >
        <span
          className="w-2 h-2 rounded-full"
          style={{
            background: connected
              ? "var(--color-success)"
              : "var(--color-error)",
          }}
          aria-hidden="true"
        />
        <span className="text-sm" style={{ color: "var(--color-text-muted)" }}>
          {connected ? "Connected" : "Disconnected"}
        </span>
      </div>
    </header>
  );
}
