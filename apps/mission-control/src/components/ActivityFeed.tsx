"use client";

import { useState, useEffect } from "react";
import { useSSE } from "@/hooks/useAgents";
import { formatRelativeTime } from "@/lib/utils";

interface ActivityEvent {
  ts: number;
  type: string;
  agent?: string;
  message?: string;
}

function isActivityEvent(val: unknown): val is ActivityEvent {
  return (
    typeof val === "object" &&
    val !== null &&
    "ts" in val &&
    typeof (val as Record<string, unknown>)["ts"] === "number" &&
    "type" in val &&
    typeof (val as Record<string, unknown>)["type"] === "string"
  );
}

export function ActivityFeed() {
  const { lastEvent } = useSSE();
  const [events, setEvents] = useState<ActivityEvent[]>([]);

  useEffect(() => {
    if (isActivityEvent(lastEvent)) {
      setEvents((prev) => [lastEvent, ...prev].slice(0, 100));
    }
  }, [lastEvent]);

  return (
    <section
      aria-label="Activity feed"
      aria-live="polite"
      className="rounded-xl border"
      style={{
        background: "var(--color-surface-2)",
        borderColor: "var(--color-border)",
      }}
    >
      <div
        className="px-5 py-4 border-b"
        style={{ borderColor: "var(--color-border)" }}
      >
        <h2 className="font-semibold text-sm">Activity Feed</h2>
      </div>
      <div>
        {events.length === 0 ? (
          <p
            className="px-5 py-4 text-sm"
            style={{ color: "var(--color-text-muted)" }}
          >
            Waiting for events…
          </p>
        ) : (
          events.map((ev, i) => (
            <div
              key={i}
              className="px-5 py-3 flex justify-between items-start border-b"
              style={{ borderColor: "var(--color-border)" }}
            >
              <div>
                <span
                  className="text-xs font-medium uppercase tracking-wider"
                  style={{ color: "var(--color-accent)" }}
                >
                  {ev.type}
                </span>
                {ev.agent != null && (
                  <span
                    className="text-xs ml-2"
                    style={{ color: "var(--color-text-muted)" }}
                  >
                    · {ev.agent}
                  </span>
                )}
                {ev.message != null && (
                  <p className="text-sm mt-0.5">{ev.message}</p>
                )}
              </div>
              <span
                className="text-xs ml-4 shrink-0"
                style={{ color: "var(--color-text-muted)" }}
              >
                {formatRelativeTime(ev.ts)}
              </span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
