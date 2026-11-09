"""
LangGraph State Definition
Shared state across all agents
"""

from typing import TypedDict, List, Optional, Dict, Any

class AgentState(TypedDict):
    """
    Shared state that flows through the agent graph
    This state is accessible by all agents and gets updated as it flows
    Nodes return only the keys they change.
    """

    # ====== IDENTIFICATION ======
    session_id: str  # Unique session identifier
    customer_id: str  # Customer identifier
    channel: str  # Current channel: mobile, whatsapp, web, store

    # ====== CONVERSATION ======
    current_request: str  # Latest customer message
    messages: List[Dict[str, Any]]  # Conversation history
    intent: Optional[str]  # Detected customer intent

    # ====== SHOPPING CONTEXT ======
    liked_products: List[str]  # Product IDs customer liked
    cart: List[Dict[str, Any]]  # Shopping cart items
    location: str  # Customer location
    use_points: bool  # True when the customer chose to pay part of the cart with loyalty points

    # ====== AGENT COORDINATION ======
    agent_calls: List[Dict[str, Any]]  # Track which agents were called this turn
    agents_needed: List[str]  # Which agents should be invoked
    blocked: bool  # True when the input checks rejected the message
    pending_approval: Optional[Dict[str, Any]]  # What the customer is being asked to approve

    # ====== AGENT RESPONSES ======
    recommendations: Optional[List[Dict[str, Any]]]  # From recommendation agent
    inventory_status: Optional[Dict[str, Any]]  # From inventory agent
    payment_status: Optional[Dict[str, Any]]  # From payment agent
    fulfillment_info: Optional[Dict[str, Any]]  # From fulfillment agent
    loyalty_info: Optional[Dict[str, Any]]  # From loyalty agent
    support_info: Optional[Dict[str, Any]]  # From support agent

    # ====== FINAL OUTPUT ======
    response: str  # Final response to customer
    next_action: Optional[str]  # What should happen next
    error: Optional[str]  # Any error messages


def create_initial_state(
    session_id: str,
    customer_id: str,
    channel: str,
    current_request: str,
    messages: List[Dict[str, Any]] = None,
    liked_products: List[str] = None,
    cart: List[Dict[str, Any]] = None,
    location: str = "Mumbai",
    use_points: bool = False
) -> AgentState:
    """
    Create initial state for one turn. Every key is reset, so results from
    an earlier turn on the same thread do not leak into this one.
    """
    return {
        "session_id": session_id,
        "customer_id": customer_id,
        "channel": channel,
        "current_request": current_request,
        "messages": messages or [],
        "intent": None,
        "liked_products": liked_products or [],
        "cart": cart or [],
        "location": location,
        "use_points": use_points,
        "agent_calls": [],
        "agents_needed": [],
        "blocked": False,
        "pending_approval": None,
        "recommendations": None,
        "inventory_status": None,
        "payment_status": None,
        "fulfillment_info": None,
        "loyalty_info": None,
        "support_info": None,
        "response": "",
        "next_action": None,
        "error": None
    }
