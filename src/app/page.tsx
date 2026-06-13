import { MissionControl } from "@/components/mission-control";
import { getMockAgentStatus } from "@/lib/agents/mock";

export default function HomePage() {
  const status = getMockAgentStatus();

  return <MissionControl agents={status.agents} />;
}
