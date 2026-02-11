from agents.base_agent import BaseAgent
from typing import Dict, Any, List
import json


# ============================================================================
# LOYALTY AGENT
# ============================================================================

class LoyaltyAgent(BaseAgent):
    
    def __init__(self):
        super().__init__(
            agent_name="Loyalty Agent",
            agent_description="Manages loyalty points, discounts, and offers"
        )
        self.customers = self._load_customers()
    
    def _load_customers(self) -> Dict[str, Any]:
        """Load customer loyalty data"""
        try:
            with open("data/customers.json", 'r') as f:
                data = json.load(f)
                customers_dict = {}
                for c in data.get("customers", []):
                    customers_dict[c["customer_id"]] = c
                return customers_dict
        except:
            # Mock customer data
            return {
                "CUST001": {
                    "customer_id": "CUST001",
                    "name": "Rahul Sharma",
                    "loyalty_points": 500,
                    "tier": "Gold"
                }
            }
    
    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate applicable offers and points
        """
        customer_id = state.get("customer_id", "CUST001")
        cart = state.get("cart", [])
        
        # Get customer loyalty info
        customer = self.customers.get(customer_id, {})
        points_available = customer.get("loyalty_points", 500)
        
        # Calculate cart value
        cart_value = sum(2500 * item.get("quantity", 1) for item in cart)
        
        # Determine applicable offers
        offers = []
        discount_amount = 0
        
        # Bundle offer
        if len(cart) >= 3:
            offers.append("Bundle Offer: 20% off on 3+ items")
            discount_amount = cart_value * 0.20
        elif len(cart) >= 2:
            offers.append("Multi-buy: 10% off on 2+ items")
            discount_amount = cart_value * 0.10
        
        # Loyalty points value
        points_value = points_available  # 1 point = ₹1
        
        # Calculate final price
        final_price = cart_value - discount_amount - min(points_value, cart_value * 0.1)
        
        return {
            "status": "calculated",
            "points_available": points_available,
            "points_value": points_value,
            "offers": offers,
            "discount_amount": discount_amount,
            "original_price": cart_value,
            "final_price": final_price,
            "savings": cart_value - final_price,
            "message": f"You're saving ₹{cart_value - final_price:.0f}!"
        }