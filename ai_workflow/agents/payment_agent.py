"""
Payment Agent
Handles payment processing with automatic retry across gateways (Edge Case #1)
"""

from typing import Any, Dict

from ai_workflow.agents.base_agent import BaseAgent
from ai_workflow.integrations.payments.charge import charge
from ai_workflow.tools.orders import create_order, loyalty_discount


class PaymentAgent(BaseAgent):
    name = "payment"
    description = "Processes payments with smart fallback mechanisms"
    result_key = "payment_status"
    needs_approval = True

    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Charge the cart total (after discounts), trying the next gateway when one fails
        """
        cart = state.get("cart", [])
        if not cart:
            return {"success": False, "status": "no_items", "message": "Your cart is empty"}

        amount = loyalty_discount(state["customer_id"], cart, state.get("use_points", False))["final_price"]
        payment = await charge(amount)
        if not payment["success"]:
            return {**payment, "status": "failed"}

        session = {"session_id": state["session_id"], "customer_id": state["customer_id"], "cart": cart}
        order = await create_order(session, payment)
        return {**payment, "status": "completed", "order_id": order["id"]}
