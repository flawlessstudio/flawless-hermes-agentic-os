import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json({
    status: "ok",
    service: "flawless-hermes-agentic-os",
    phase: "scaffold",
    adaptersEnabled: false,
    timestamp: new Date().toISOString()
  });
}
