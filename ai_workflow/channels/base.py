"""Runs one customer message through the graph, whichever channel it came from."""

from dataclasses import dataclass
from typing import Any, Dict, List

from langgraph.types import Command
from loguru import logger

from ai_workflow.channels.websocket_manager import ConnectionManager
from ai_workflow.graph.state import create_initial_state
from ai_workflow.storage import redis_store

ERROR_REPLY = "I apologize, but I'm having trouble processing your request. Please try again."
NOTHING_TO_APPROVE_REPLY = "There is nothing waiting for your approval."
MAX_HISTORY_ENTRIES = 100


@dataclass
class IncomingMessage:
    session_id: str
    text: str
    channel: str = "web"  # mobile, whatsapp, web, store


async def handle_message(msg: IncomingMessage, graph, manager: ConnectionManager) -> Dict[str, Any]:
    """Run the graph for a message. Returns response, recommendations, agents_used, pending_approval, blocked."""
    session = redis_store.get_session(msg.session_id)
    await manager.send_agent_update(msg.session_id, {
        "type": "orchestrator_start",
        "message": "Analyzing request...",
        "request": msg.text
    })
    state = create_initial_state(
        session_id=msg.session_id,
        customer_id=session["customer_id"],
        channel=msg.channel,
        current_request=msg.text,
        messages=session.get("conversation_history", []),
        liked_products=session.get("liked_products", []),
        cart=session.get("cart", []),
        location=session.get("location", "Mumbai"),
        use_points=session.get("use_points", False),
    )
    return await _run_graph(graph, state, msg.session_id, manager)


async def resume_after_approval(session_id: str, approved: bool, graph, manager: ConnectionManager) -> Dict[str, Any]:
    """Continue a graph that is paused for approval. Returns the same shape as handle_message."""
    paused = await graph.aget_state({"configurable": {"thread_id": session_id}})
    if not paused.next:
        return _reply(NOTHING_TO_APPROVE_REPLY)
    return await _run_graph(graph, Command(resume={"approved": approved}), session_id, manager)


async def _run_graph(graph, graph_input, session_id: str, manager: ConnectionManager) -> Dict[str, Any]:
    config = {"configurable": {"thread_id": session_id}}
    try:
        # After an approval answer the agents to run are already in the paused state
        agents_needed: List[str] = []
        if isinstance(graph_input, Command):
            agents_needed = (await graph.aget_state(config)).values.get("agents_needed", [])

        interrupts = None
        async for update in graph.astream(graph_input, config=config, stream_mode="updates"):
            for node, change in update.items():
                if node == "__interrupt__":
                    interrupts = change
                elif node == "check_input" and change.get("blocked"):
                    await manager.send_agent_update(session_id, {"type": "input_blocked", "reason": change["error"]})
                elif node == "orchestrator":
                    agents_needed = change["agents_needed"]
                    await _send_agent_call(manager, session_id, "orchestrator", "success")
                elif node == "ask_for_approval":
                    agents_needed = (change or {}).get("agents_needed", agents_needed)
                    for name in agents_needed:
                        await _send_agent_call(manager, session_id, name, "processing")
                elif node == "call_agents":
                    for call in change["agent_calls"]:
                        if call["agent"] != "orchestrator":
                            await _send_agent_call(manager, session_id, call["agent"], call["status"])

        result = (await graph.aget_state(config)).values

        if interrupts:
            pending = interrupts[0].value
            await manager.send_agent_update(session_id, {"type": "approval_needed", **pending})
            return _reply(pending["summary"], agents_used=result["agent_calls"], pending_approval=pending)

        _save_conversation(session_id, result)
        await manager.send_agent_update(session_id, {
            "type": "orchestrator_complete",
            "response": result["response"],
            "agents_used": result["agent_calls"]
        })
        return _reply(
            result["response"],
            result.get("recommendations"),
            result["agent_calls"],
            blocked=result["blocked"],
            order_id=(result["payment_status"] or {}).get("order_id"),
        )

    except Exception as e:
        logger.error("Error in graph: {}", e)
        return {"success": False, "response": ERROR_REPLY}


async def _send_agent_call(manager: ConnectionManager, session_id: str, agent: str, status: str) -> None:
    await manager.send_agent_update(session_id, {
        "type": "agent_called",
        "agent": agent,
        "status": status,
        "message": f"{agent} {status}"
    })


def _save_conversation(session_id: str, result: Dict[str, Any]) -> None:
    """Add the exchange to the history. A paid order empties the cart."""
    def add_exchange(session):
        session["conversation_history"].append({
            "role": "user",
            "content": result["current_request"],
            "channel": result["channel"]
        })
        session["conversation_history"].append({
            "role": "assistant",
            "content": result["response"],
            "channel": result["channel"]
        })
        session["conversation_history"] = session["conversation_history"][-MAX_HISTORY_ENTRIES:]
        if (result["payment_status"] or {}).get("success"):
            session["cart"] = []
            session["use_points"] = False

    redis_store.update_session(session_id, add_exchange)


def _reply(
    response: str, recommendations=None, agents_used=None, pending_approval=None, blocked=False, order_id=None
) -> Dict[str, Any]:
    return {
        "response": response,
        "recommendations": recommendations,
        "agents_used": agents_used or [],
        "pending_approval": pending_approval,
        "blocked": blocked,
        "order_id": order_id,
    }
