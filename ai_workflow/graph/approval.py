"""Pauses the graph until the customer approves actions that need approval."""

from typing import Any, Dict

from langgraph.types import interrupt

from ai_workflow.agents import AGENTS
from ai_workflow.tools.cart import cart_total
from ai_workflow.tools.orders import loyalty_discount


def ask_for_approval(state: Dict[str, Any]) -> Dict[str, Any]:
    """Ask the customer before any agent marked needs_approval runs. Resume value: {"approved": bool}."""
    agents_needed = state["agents_needed"]
    needs_approval = [name for name in agents_needed if AGENTS[name].needs_approval]
    if not needs_approval or not state["cart"]:
        return {}

    items = cart_total(state["cart"])["items"]
    amount = loyalty_discount(state["customer_id"], state["cart"], state.get("use_points", False))["final_price"]
    item_text = ", ".join(f"{item['name']} x{item['quantity']}" for item in items)
    decision = interrupt({
        "summary": f"Place this order? {item_text}. Total after discounts: ₹{amount:.0f}",
        "amount": amount,
    })

    if decision["approved"]:
        return {}
    return {
        "agents_needed": [name for name in agents_needed if name not in needs_approval],
        "next_action": "payment_cancelled",
    }
