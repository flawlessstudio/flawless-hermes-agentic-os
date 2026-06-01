"use client";

import { useState } from "react";
import { api, type MemoryResult } from "@/lib/api";
import { truncate } from "@/lib/utils";

export function MemoryPanel() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MemoryResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const search = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setHasSearched(true);
    try {
      const data = await api.memory.query(query);
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section
      aria-label="Memory search"
      className="rounded-xl border flex flex-col"
      style={{
        background: "var(--color-surface-2)",
        borderColor: "var(--color-border)",
        minHeight: 400,
      }}
    >
      <div
        className="px-5 py-4 border-b"
        style={{ borderColor: "var(--color-border)" }}
      >
        <h2 className="font-semibold text-sm">Memory Search</h2>
      </div>
      <div className="p-5 flex flex-col gap-4 flex-1">
        <form onSubmit={(e) => void search(e)} className="flex gap-2">
          <label htmlFor="memory-query" className="sr-only">
            Search memory
          </label>
          <input
            id="memory-query"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search agent memory…"
            className="flex-1 px-3 py-2 rounded-lg text-sm border bg-transparent"
            style={{
              borderColor: "var(--color-border)",
              color: "var(--color-text)",
              outline: "none",
            }}
            disabled={loading}
            aria-busy={loading}
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-4 py-2 rounded-lg text-sm font-medium"
            style={{
              background: "var(--color-accent)",
              color: "white",
              opacity: loading || !query.trim() ? 0.5 : 1,
              cursor: loading || !query.trim() ? "not-allowed" : "pointer",
              border: "none",
            }}
          >
            {loading ? "…" : "Search"}
          </button>
        </form>

        {error != null && (
          <p role="alert" className="text-sm" style={{ color: "var(--color-error)" }}>
            {error}
          </p>
        )}

        <ul className="flex flex-col gap-3 flex-1 overflow-y-auto" aria-label="Search results">
          {results.length === 0 && !loading && hasSearched && (
            <li className="text-sm" style={{ color: "var(--color-text-muted)" }}>
              No results found.
            </li>
          )}
          {results.map((r) => (
            <li
              key={r.id}
              className="rounded-lg p-3 border"
              style={{
                background: "var(--color-surface)",
                borderColor: "var(--color-border)",
              }}
            >
              <p className="text-sm leading-relaxed">{truncate(r.content, 120)}</p>
              <div className="flex justify-between mt-2">
                <span
                  className="text-xs"
                  style={{ color: "var(--color-text-muted)" }}
                >
                  {r.agent_id}
                </span>
                <span
                  className="text-xs font-mono"
                  style={{ color: "var(--color-accent)" }}
                  aria-label={`Relevance score: ${(r.score * 100).toFixed(0)}%`}
                >
                  {(r.score * 100).toFixed(0)}%
                </span>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
