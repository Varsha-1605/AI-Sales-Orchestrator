"""
Payment Agent
Handles payment processing with automatic retry logic (Edge Case #1)
"""

from agents.base_agent import BaseAgent
from typing import Dict, Any, List
import asyncio
import random

class PaymentAgent(BaseAgent):
    
    def __init__(self):
        super().__init__(
            agent_name="Payment Agent",
            agent_description="Processes payments with smart fallback mechanisms"
        )
        self.gateways = [
            {"name": "Razorpay", "success_rate": 0.3, "timeout": 1.2},
            {"name": "PayU", "success_rate": 0.3, "timeout": 0.8},
            {"name": "UPI Direct", "success_rate": 1.0, "timeout": 0.7}
        ]
    
    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process payment with automatic retry on failure
        """
        request = state.get("current_request", "").lower()
        cart = state.get("cart", [])
        
        # Calculate total amount
        total_amount = self._calculate_total(cart)
        
        # Check if payment should be processed
        if "pay" in request or "checkout" in request or "purchase" in request:
            return await self._process_payment_with_retry(total_amount)
        else:
            return {
                "status": "pending",
                "amount": total_amount,
                "message": "Ready to process payment"
            }
    
    async def _process_payment_with_retry(self, amount: float) -> Dict[str, Any]:
        """
        EDGE CASE #1: Payment Retry Logic
        Try multiple gateways automatically until success
        """
        retry_history = []
        
        for gateway in self.gateways:
            print(f"💳 Trying {gateway['name']}...")
            
            # Simulate payment attempt
            success = await self._attempt_payment(gateway)
            
            retry_history.append({
                "gateway": gateway["name"],
                "status": "success" if success else "failed",
                "timestamp": asyncio.get_event_loop().time()
            })
            
            if success:
                return {
                    "success": True,
                    "status": "completed",
                    "amount": amount,
                    "gateway": gateway["name"],
                    "transaction_id": f"TXN{random.randint(100000, 999999)}",
                    "retry_history": retry_history,
                    "total_time": f"{sum(g['timeout'] for g in self.gateways[:len(retry_history)]):.1f}s",
                    "message": f"Payment successful via {gateway['name']}!"
                }
        
        # All gateways failed
        return {
            "success": False,
            "status": "failed",
            "amount": amount,
            "retry_history": retry_history,
            "message": "All payment methods failed. Please try again later."
        }
    
    async def _attempt_payment(self, gateway: Dict) -> bool:
        """
        Simulate payment attempt with gateway
        """
        # Simulate network delay
        await asyncio.sleep(gateway["timeout"])
        
        # Simulate success/failure based on success rate
        return random.random() < gateway["success_rate"]
    
    def _calculate_total(self, cart: List[Dict]) -> float:
        """
        Calculate cart total
        """
        if not cart:
            return 3950.0  # Mock amount for demo
        
        total = 0
        for item in cart:
            # Mock prices
            price = 2500  # Default product price
            quantity = item.get("quantity", 1)
            total += price * quantity
        
        return total
    
    def _apply_discounts(self, amount: float, loyalty_points: int = 0) -> float:
        """
        Apply loyalty points and discounts
        """
        # Deduct loyalty points (1 point = ₹1)
        amount -= loyalty_points
        
        # Apply bundle discount if applicable
        if amount > 3000:
            amount *= 0.8  # 20% off
        
        return amount