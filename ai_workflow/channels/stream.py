"""Sends a reply to the browser piece by piece as server-sent events.

A request produces these events, in order:
  progress  an agent started or finished, a payment gateway was tried, or the guard blocked the message
  token     the next piece of the reply text (many of these)
  done      the full reply object, the same shape the non-streaming endpoint returns
"""

import asyncio
import json
import re
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List

from ai_workflow.channels.websocket_manager import ConnectionManager
from ai_workflow.settings import settings

PROGRESS_EVENT_TYPES = {"agent_called", "payment_status", "input_blocked"}
WORDS_PER_PIECE = 3


class EventCollector:
    """Takes the place of the WebSocket manager for one request: forwards every update to the
    real manager (so the agent monitor still sees it) and keeps a copy for the stream."""

    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self.queue: asyncio.Queue = asyncio.Queue()

    async def send_agent_update(self, session_id: str, message: Dict[str, Any]) -> None:
        await self.manager.send_agent_update(session_id, message)
        await self.queue.put(message)


def split_into_pieces(text: str) -> List[str]:
    """Break a reply into pieces of a few words, keeping spaces and line breaks."""
    words = re.findall(r"\S+\s*", text)
    return ["".join(words[i:i + WORDS_PER_PIECE]) for i in range(0, len(words), WORDS_PER_PIECE)]


def format_event(name: str, data: Dict[str, Any]) -> str:
    return f"event: {name}\ndata: {json.dumps(data)}\n\n"


async def stream_reply(
    manager: ConnectionManager,
    run: Callable[[EventCollector], Awaitable[Dict[str, Any]]],
) -> AsyncIterator[str]:
    """Run the graph through `run` and yield server-sent events while it works."""
    collector = EventCollector(manager)

    async def run_then_close() -> Dict[str, Any]:
        try:
            return await run(collector)
        finally:
            await collector.queue.put(None)

    task = asyncio.create_task(run_then_close())
    while (message := await collector.queue.get()) is not None:
        if message["type"] in PROGRESS_EVENT_TYPES:
            yield format_event("progress", message)

    reply = await task
    for piece in split_into_pieces(reply["response"]):
        yield format_event("token", {"text": piece})
        await asyncio.sleep(settings.STREAM_PIECE_DELAY_SECONDS)
    yield format_event("done", reply)
