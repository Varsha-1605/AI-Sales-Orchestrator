from ai_workflow.channels.base import IncomingMessage, handle_message, resume_after_approval
from ai_workflow.storage import redis_store


async def test_handle_message_returns_a_response(graph, manager, session_id):
    reply = await handle_message(IncomingMessage(session_id, "hello", "web"), graph, manager)

    assert reply["response"].startswith("Hello!")
    assert reply["pending_approval"] is None


async def test_handle_message_sends_websocket_updates_and_saves_the_conversation(graph, manager, session_id):
    await handle_message(IncomingMessage(session_id, "show me ties", "whatsapp"), graph, manager)

    assert manager.types[0] == "orchestrator_start"
    assert "agent_called" in manager.types
    assert manager.types[-1] == "orchestrator_complete"
    history = redis_store.get_session(session_id)["conversation_history"]
    assert [entry["role"] for entry in history] == ["user", "assistant"]
    assert history[0]["channel"] == "whatsapp"


async def test_handle_message_returns_pending_approval_before_payment(graph, manager, session_id):
    redis_store.add_to_cart(session_id, "VH001")

    reply = await handle_message(IncomingMessage(session_id, "checkout please", "web"), graph, manager)

    assert reply["pending_approval"]["amount"] == 2500
    assert "approval_needed" in manager.types
    assert "orchestrator_complete" not in manager.types


async def test_a_paid_order_empties_the_shared_cart(graph, manager, session_id):
    redis_store.add_to_cart(session_id, "VH001")
    await handle_message(IncomingMessage(session_id, "checkout please", "whatsapp"), graph, manager)

    reply = await resume_after_approval(session_id, True, graph, manager)

    assert "Order confirmed" in reply["response"]
    assert reply["order_id"].startswith("ORD")
    assert redis_store.get_session(session_id)["cart"] == []
