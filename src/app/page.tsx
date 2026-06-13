import { getMockAgentStatus } from "@/lib/agents/mock";
import { RUNTIME_POLICY } from "@/lib/policy/runtime";

export default function HomePage() {
  const status = getMockAgentStatus();

  return (
    <main>
      <p className="eyebrow">Flawless Studio · Local status</p>
      <h1>Mission Control</h1>
      <p className="lede">A server-rendered scaffold using deterministic local data.</p>

      <section className="grid" aria-label="System layers">
        {status.agents.map((item) => (
          <article key={item.id}>
            <span className="badge">Mock</span>
            <h2>{item.name}</h2>
            <p>{item.role}</p>
            <small>{item.detail}</small>
          </article>
        ))}
      </section>

      <section className="policy" aria-label="Runtime feature state">
        <h2>Runtime boundary</h2>
        {Object.entries(RUNTIME_POLICY).map(([name, enabled]) => (
          <div key={name}><code>{name}</code><strong>{enabled ? "Enabled" : "Disabled"}</strong></div>
        ))}
      </section>
    </main>
  );
}
