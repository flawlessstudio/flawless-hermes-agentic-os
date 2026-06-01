"""SSE streaming endpoint for real-time agent events."""
from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/stream", tags=["stream"])


async def _event_generator():
    """Generate SSE heartbeat events."""
    while True:
        data = json.dumps({"ts": time.time(), "type": "heartbeat"})
        yield f"data: {data}\n\n"
        await asyncio.sleep(5)


@router.get("/events")
async def stream_events() -> StreamingResponse:
    """Server-Sent Events stream for real-time Mission Control updates."""
    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
