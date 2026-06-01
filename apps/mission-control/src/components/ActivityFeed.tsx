"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface ActivityEvent {
  id: string;
  ts: number;
  type: "agent_status" | "heartbeat" | "error" | "info";
  message: string;
}

/**
 * ActivityFeed — real-time event log panel.
 *
 * Displays a scrollable, auto-scroll-to-bottom list of events.
 * Auto-pauses scrolling when the user scrolls up.
 */
export function ActivityFeed({ className }: { className?: string }) {
  const [events, setEvents] = useState<ActivityEvent[]>([
    {
      id: "init",
      ts: Date.now() / 1000,
      type: "info",
      message: "Mission Control initialised",
    },
  ]);
  const [autoScroll, setAutoScroll] = useState(true);
  const listRef = useRef<HTMLUListElement>(null);

  // Auto-scroll when new events arrive and autoScroll is enabled.
  useEffect(() => {
    if (autoScroll && listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  // Listen to SSE stream and add events.
  useEffect(() => {
    const API_BASE =
      typeof window !== "undefined"
        ? (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
        : "http://localhost:8000";

    const es = new EventSource(`${API_BASE}/stream/events`);

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data as string) as {
          type: string;
          ts: number;
        };
        const event: ActivityEvent = {
          id: `${data.ts}-${Math.random()}`,
          ts: data.ts,
          type:
            data.type === "heartbeat"
              ? "heartbeat"
              : data.type === "agent_status"
                ? "agent_status"
                : "info",
          message:
            data.type === "heartbeat"
              ? "Heartbeat received"
              : `Event: ${data.type}`,
        };
        setEvents((prev) => [...prev.slice(-99), event]);
      } catch {
        // Ignore parse errors
      }
    };

    es.onerror = () => {
      setEvents((prev) => [
        ...prev.slice(-99),
        {
          id: `err-${Date.now()}`,
          ts: Date.now() / 1000,
          type: "error",
          message: "SSE connection lost",
        },
      ]);
    };

    return () => es.close();
  }, []);

  function handleScroll() {
    if (!listRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = listRef.current;
    const atBottom = scrollHeight - scrollTop - clientHeight < 40;
    setAutoScroll(atBottom);
  }

  const typeColour: Record<ActivityEvent["type"], string> = {
    agent_status: "var(--color-info)",
    heartbeat: "var(--color-text-subtle)",
    error: "var(--color-error)",
    info: "var(--color-success)",
  };

  const typeLabel: Record<ActivityEvent["type"], string> = {
    agent_status: "STATUS",
    heartbeat: "PING",
    error: "ERROR",
    info: "INFO",
  };

  return (
    <section
      className={cn("flex flex-col gap-3", className)}
      aria-labelledby="activity-feed-heading"
    >
      <div className="flex items-center justify-between">
        <h2
          id="activity-feed-heading"
          className="text-sm font-semibold"
          style={{ color: "var(--color-text)" }}
        >
          Activity Feed
        </h2>
        {!autoScroll && (
          <button
            onClick={() => {
              setAutoScroll(true);
              if (listRef.current) {
                listRef.current.scrollTop = listRef.current.scrollHeight;
              }
            }}
            className="text-xs px-2 py-1 rounded"
            style={{
              background: "var(--color-accent-subtle)",
              color: "var(--color-accent)",
            }}
          >
            ↓ Latest
          </button>
        )}
      </div>

      <ul
        ref={listRef}
        onScroll={handleScroll}
        className="flex flex-col gap-1 overflow-y-auto max-h-48"
        aria-label="Activity events"
        aria-live="polite"
        aria-atomic="false"
        aria-relevant="additions"
      >
        {events.map((ev) => (
          <li
            key={ev.id}
            className="flex items-start gap-2 text-xs"
            style={{ color: "var(--color-text-muted)" }}
          >
            <span
              className="font-mono flex-shrink-0"
              style={{ color: "var(--color-text-subtle)" }}
            >
              {new Date(ev.ts * 1000).toLocaleTimeString()}
            </span>
            <span
              className="font-mono flex-shrink-0 px-1 rounded text-xs"
              style={{
                color: typeColour[ev.type],
                background: `${typeColour[ev.type]}20`,
              }}
            >
              {typeLabel[ev.type]}
            </span>
            <span>{ev.message}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
