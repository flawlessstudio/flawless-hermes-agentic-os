import { NextResponse } from "next/server";

import { getMockAgentStatus } from "@/lib/agents/mock";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json(getMockAgentStatus());
}
