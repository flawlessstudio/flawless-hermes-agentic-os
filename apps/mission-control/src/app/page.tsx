import { AgentGrid } from "@/components/AgentGrid";
import { ActivityFeed } from "@/components/ActivityFeed";
import { StatusBar } from "@/components/StatusBar";
import { MemoryPanel } from "@/components/MemoryPanel";

export default function MissionControlPage() {
  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--color-bg)" }}>
      <StatusBar />
      <main
        id="main-content"
        className="flex-1 grid gap-6 p-6"
        style={{ gridTemplateColumns: "1fr" }}
      >
        <div className="flex flex-col gap-6">
          <h1
            className="text-2xl font-bold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            Mission Control
          </h1>
          <div className="grid gap-6" style={{ gridTemplateColumns: "1fr" }}>
            <AgentGrid />
            <div className="grid gap-6" style={{ gridTemplateColumns: "1fr 360px" }}>
              <ActivityFeed />
              <aside aria-label="Memory panel">
                <MemoryPanel />
              </aside>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
