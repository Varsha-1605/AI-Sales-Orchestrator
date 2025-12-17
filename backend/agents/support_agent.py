from agents.base_agent import BaseAgent
from typing import Dict, Any, List
import json

# ============================================================================
# SUPPORT AGENT
# ============================================================================

class SupportAgent(BaseAgent):
    
    def __init__(self):
        super().__init__(
            agent_name="Support Agent",
            agent_description="Handles returns, exchanges, and customer issues"
        )
    
    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle support queries
        """
        request = state.get("current_request", "").lower()
        
        # Return request
        if "return" in request or "refund" in request:
            return self._handle_return_request()
        
        # Exchange request
        elif "exchange" in request or "replace" in request:
            return self._handle_exchange_request()
        
        # General help
        elif "help" in request or "issue" in request:
            return self._provide_general_help()
        
        else:
            return {
                "status": "ready",
                "message": "I'm here to help! You can ask about returns, exchanges, or any issues."
            }
    
    def _handle_return_request(self) -> Dict[str, Any]:
        """
        Process return eligibility
        """
        return {
            "status": "eligible",
            "return_window": "30 days",
            "conditions": ["Unused with tags", "Original packaging"],
            "refund_timeline": "5-7 days",
            "pickup_available": True,
            "message": "You can return this item within 30 days. Pickup can be scheduled."
        }
    
    def _handle_exchange_request(self) -> Dict[str, Any]:
        """
        Process exchange request
        """
        return {
            "status": "eligible",
            "exchange_options": ["Different size", "Different color", "Different product"],
            "timeline": "3-5 days for exchange",
            "cost": "Free exchange",
            "message": "We can arrange an exchange. What would you like instead?"
        }
    
    def _provide_general_help(self) -> Dict[str, Any]:
        """
        Provide general support info
        """
        return {
            "status": "available",
            "help_topics": [
                "Order tracking",
                "Returns & Exchanges",
                "Payment issues",
                "Product questions"
            ],
            "contact": {
                "phone": "1800-XXX-XXXX",
                "email": "support@vanheusen.com",
                "chat": "Available 24/7"
            },
            "message": "I can help you with orders, returns, or any questions!"
        }