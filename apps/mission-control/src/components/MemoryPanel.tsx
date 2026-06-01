"use client";

import { useState, useTransition } from "react";
import { searchMemory, type MemoryQueryResult } from "@/lib/api";
import { cn, truncate } from "@/lib/utils";

/**
 * MemoryPanel — semantic search over agent memory.
 *
 * Provides a search input + result list.  Uses React transitions so
 * the UI remains responsive during fetch.
 */
export function MemoryPanel({ className }: { className?: string }) {
  const [agentId, setAgentId] = useState("research_1");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MemoryQueryResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    startTransition(async () => {
      try {
        const data = await searchMemory({ agent_id: agentId, query, n: 8 });
        setResults(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Search failed");
        setResults([]);
      }
    });
  }

  return (
    <section
      className={cn("flex flex-col gap-4", className)}
      aria-labelledby="memory-panel-heading"
    >
      <h2
        id="memory-panel-heading"
        className="text-lg font-semibold"
        style={{ color: "var(--color-text)" }}
      >
        Memory Search
      </h2>

      <form onSubmit={handleSearch} className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <label
            htmlFor="memory-agent-id"
            className="text-xs"
            style={{ color: "var(--color-text-muted)" }}
          >
            Agent ID
          </label>
          <input
            id="memory-agent-id"
            type="text"
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
            placeholder="agent_id"
            className="rounded px-3 py-2 text-sm"
            style={{
              background: "var(--color-surface-2)",
              border: "1px solid var(--color-border)",
              color: "var(--color-text)",
              outline: "none",
            }}
            onFocus={(e) =>
              (e.currentTarget.style.borderColor = "var(--color-border-focus)")
            }
            onBlur={(e) =>
              (e.currentTarget.style.borderColor = "var(--color-border)")
            }
          />
        </div>

        <div className="flex flex-col gap-1">
          <label
            htmlFor="memory-query"
            className="text-xs"
            style={{ color: "var(--color-text-muted)" }}
          >
            Query
          </label>
          <input
            id="memory-query"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search memories…"
            className="rounded px-3 py-2 text-sm"
            style={{
              background: "var(--color-surface-2)",
              border: "1px solid var(--color-border)",
              color: "var(--color-text)",
              outline: "none",
            }}
            onFocus={(e) =>
              (e.currentTarget.style.borderColor = "var(--color-border-focus)")
            }
            onBlur={(e) =>
              (e.currentTarget.style.borderColor = "var(--color-border)")
            }
          />
        </div>

        <button
          type="submit"
          disabled={isPending || !query.trim()}
          className="rounded px-4 py-2 text-sm font-medium transition-opacity"
          style={{
            background: "var(--color-accent)",
            color: "#fff",
            opacity: isPending || !query.trim() ? 0.6 : 1,
            cursor: isPending || !query.trim() ? "not-allowed" : "pointer",
          }}
          aria-busy={isPending}
        >
          {isPending ? "Searching…" : "Search"}
        </button>
      </form>

      {error && (
        <p
          role="alert"
          className="text-sm rounded px-3 py-2"
          style={{
            background: "var(--color-error-subtle)",
            color: "var(--color-error)",
          }}
        >
          {error}
        </p>
      )}

      {results.length > 0 && (
        <ul className="flex flex-col gap-2" aria-label="Search results">
          {results.map((r) => (
            <li
              key={r.entry.id}
              className="rounded p-3 flex flex-col gap-1"
              style={{
                background: "var(--color-surface-2)",
                border: "1px solid var(--color-border)",
              }}
            >
              <p
                className="text-sm"
                style={{ color: "var(--color-text)" }}
              >
                {truncate(r.entry.content, 140)}
              </p>
              <span
                className="text-xs"
                style={{ color: "var(--color-text-muted)" }}
              >
                Relevance: {(r.relevance_score * 100).toFixed(1)}%
              </span>
            </li>
          ))}
        </ul>
      )}

      {!isPending && results.length === 0 && query && !error && (
        <p className="text-sm" style={{ color: "var(--color-text-subtle)" }}>
          No results found.
        </p>
      )}
    </section>
  );
}
