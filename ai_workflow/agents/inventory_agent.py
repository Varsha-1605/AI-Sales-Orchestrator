"""
Inventory Agent
Handles stock checking, store location, and reservations
"""

from typing import Any, Dict, List

from ai_workflow.agents.base_agent import BaseAgent
from ai_workflow.tools.catalog import check_stock

DEFAULT_PRODUCT_ID = "VH001"
DEFAULT_SIZE = "40"


class InventoryAgent(BaseAgent):
    name = "inventory"
    description = "Checks stock availability and finds alternative locations"
    result_key = "inventory_status"

    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check inventory and provide alternatives
        """
        request = state.get("current_request", "").lower()
        cart = state.get("cart", [])
        location = state.get("location", "Mumbai")

        asks_about_one_item = "stock" in request or "available" in request or "store" in request or "nearby" in request
        if asks_about_one_item:
            # Check the first cart item, or the default product when the cart is empty
            item = cart[0] if cart else {"product_id": DEFAULT_PRODUCT_ID}
            return check_stock(item["product_id"], item.get("size", DEFAULT_SIZE), location)

        if cart:
            return self._check_cart_availability(cart, location)
        return {"available": True, "message": "All items in stock"}

    def _check_cart_availability(self, cart: List[Dict[str, Any]], location: str) -> Dict[str, Any]:
        """
        Check if all cart items are available
        """
        unavailable_items = [
            item["product_id"]
            for item in cart
            if not check_stock(item["product_id"], item.get("size", DEFAULT_SIZE), location)["available"]
        ]
        all_available = not unavailable_items
        return {
            "available": all_available,
            "unavailable_items": unavailable_items,
            "message": "All items available" if all_available else "Some items unavailable"
        }
