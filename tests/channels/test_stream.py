import json

from ai_workflow.channels.base import IncomingMessage, handle_message
from ai_workflow.channels.stream import split_into_pieces, stream_reply


def parse_events(body: str):
    events = []
    for block in body.split("\n\n"):
        if block.strip():
            name_line, data_line = block.splitlines()[:2]
            events.append((name_line.removeprefix("event: "), json.loads(data_line.removeprefix("data: "))))
    return events


def test_a_reply_is_split_into_short_pieces_that_rejoin_exactly():
    text = "I found 3 items that would look amazing on you!\n\n**Silk Tie** (₹800)\n   Pairs perfectly\n"

    pieces = split_into_pieces(text)

    assert "".join(pieces) == text
    assert all(len(piece.split()) <= 3 for piece in pieces)
    assert len(pieces) > 1


async def test_stream_sends_progress_then_text_pieces_then_the_full_reply(graph, manager, session_id):
    message = IncomingMessage(session_id, "show me ties", "web")

    chunks = [chunk async for chunk in stream_reply(manager, lambda sender: handle_message(message, graph, sender))]
    events = parse_events("".join(chunks))

    names = [name for name, _ in events]
    assert names[0] == "progress"
    assert names[-1] == "done"
    assert names.index("token") > max(i for i, name in enumerate(names) if name == "progress")
    streamed_text = "".join(data["text"] for name, data in events if name == "token")
    assert streamed_text == events[-1][1]["response"]


def test_stream_endpoint_returns_server_sent_events(client):
    session_id = client.post("/api/session/create?customer_id=CUST001").json()["session_id"]

    response = client.post("/api/chat/stream", json={"session_id": session_id, "message": "hello", "channel": "web"})

    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_events(response.text)
    assert events[-1][0] == "done"
    assert events[-1][1]["response"].startswith("Hello!")
