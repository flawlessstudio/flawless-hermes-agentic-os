"use client";

import { motion } from "framer-motion";

import type { AgentHealth } from "@/lib/agents/types";
import { POLICY_RULES } from "@/lib/policy/permissions";

interface MissionControlProps {
  agents: AgentHealth[];
}

const stateLabels: Record<AgentHealth["state"], string> = {
  live: "Live",
  degraded: "Degraded",
  offline: "Offline",
  mock: "Mock"
};

export function MissionControl({ agents }: MissionControlProps) {
  return (
    <main className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Flawless Studio · Local Mission Control</p>
          <h1>Hermes Agentic OS</h1>
          <p className="lede">
            A verified, read-only scaffold for observing declared agent roles before local adapters are enabled.
          </p>
        </div>
        <div className="phase-card" aria-label="Current implementation phase">
          <span>Phase</span>
          <strong>Validated scaffold</strong>
          <small>Adapters disabled</small>
        </div>
      </header>

      <section aria-labelledby="agent-status-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">System status</p>
            <h2 id="agent-status-title">Agent layers</h2>
          </div>
          <p>Data source: deterministic local mock</p>
        </div>

        <div className="agent-grid">
          {agents.map((agent, index) => (
            <motion.article
              className="agent-card"
              key={agent.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <div className="card-topline">
                <span className={`status-dot status-${agent.state}`} aria-hidden="true" />
                <span className="status-label">{stateLabels[agent.state]}</span>
              </div>
              <h3>{agent.name}</h3>
              <p className="role">{agent.role}</p>
              <p>{agent.detail}</p>
              <dl>
                <div>
                  <dt>Source</dt>
                  <dd>{agent.source}</dd>
                </div>
                <div>
                  <dt>Last checked</dt>
                  <dd>{new Date(agent.lastCheckedAt).toLocaleString()}</dd>
                </div>
              </dl>
            </motion.article>
          ))}
        </div>
      </section>

      <section className="policy-section" aria-labelledby="policy-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Safety boundary</p>
            <h2 id="policy-title">Permission policy</h2>
          </div>
          <p>Deny by default; explicit approval for consequential capabilities.</p>
        </div>

        <div className="policy-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Capability</th>
                <th>Decision</th>
                <th>Rationale</th>
              </tr>
            </thead>
            <tbody>
              {POLICY_RULES.map((rule) => (
                <tr key={rule.capability}>
                  <td><code>{rule.capability}</code></td>
                  <td><span className={`decision decision-${rule.decision}`}>{rule.decision}</span></td>
                  <td>{rule.rationale}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <footer>
        <p>This scaffold performs no consequential operation and uses no paid service.</p>
      </footer>
    </main>
  );
}
