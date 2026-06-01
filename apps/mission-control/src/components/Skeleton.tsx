export function AgentCardSkeleton() {
  return (
    <div
      className="rounded-xl p-5 border flex flex-col gap-3"
      style={{
        background: "var(--color-surface-2)",
        borderColor: "var(--color-border)",
        animation: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      }}
      aria-hidden="true"
    >
      <div className="flex justify-between items-center">
        <div
          className="h-4 rounded"
          style={{ background: "var(--color-border)", width: 96 }}
        />
        <div
          className="h-3 rounded"
          style={{ background: "var(--color-border)", width: 48 }}
        />
      </div>
      <div className="flex gap-1">
        {[60, 48, 72].map((w) => (
          <div
            key={w}
            className="h-5 rounded"
            style={{ background: "var(--color-border)", width: w }}
          />
        ))}
      </div>
      <div
        className="h-3 rounded"
        style={{ background: "var(--color-border)", width: 128 }}
      />
    </div>
  );
}
