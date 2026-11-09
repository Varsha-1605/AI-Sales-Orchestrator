from typing import Any, Dict

from ai_workflow.agents.base_agent import BaseAgent
from ai_workflow.tools.orders import loyalty_discount


# ============================================================================
# LOYALTY AGENT
# ============================================================================

class LoyaltyAgent(BaseAgent):
    name = "loyalty"
    description = "Manages loyalty points, discounts, and offers"
    result_key = "loyalty_info"

    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate applicable offers and points
        """
        discount = loyalty_discount(state.get("customer_id", "CUST001"), state.get("cart", []), state.get("use_points", False))
        return {
            "status": "calculated",
            **discount,
            "message": f"You're saving ₹{discount['savings']:.0f}!"
        }
