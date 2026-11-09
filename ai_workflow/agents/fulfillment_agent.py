from typing import Any, Dict

from ai_workflow.agents.base_agent import BaseAgent
from ai_workflow.tools.orders import delivery_options

# ============================================================================
# FULFILLMENT AGENT
# ============================================================================

class FulfillmentAgent(BaseAgent):
    name = "fulfillment"
    description = "Handles delivery scheduling and order management"
    result_key = "fulfillment_info"

    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Arrange delivery for orders
        """
        return delivery_options(state.get("cart", []), state.get("location", "Mumbai"))
