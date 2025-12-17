"""
LangGraph Multi-Agent Orchestrator
Coordinates all 6 specialized agents
"""

from langgraph.graph import StateGraph, END
from typing import Dict, Any
import asyncio

from graph.state import AgentState
from agents.recommendation_agent import RecommendationAgent
from agents.inventory_agent import InventoryAgent
from agents.payment_agent import PaymentAgent
from agents.fulfillment_agent import FulfillmentAgent
from agents.loyalty_agent import LoyaltyAgent
from agents.support_agent import SupportAgent
from config import settings

# ============================================================================
# AGENT INSTANCES
# ============================================================================

recommendation_agent = RecommendationAgent()
inventory_agent = InventoryAgent()
payment_agent = PaymentAgent()
fulfillment_agent = FulfillmentAgent()
loyalty_agent = LoyaltyAgent()
support_agent = SupportAgent()

# ============================================================================
# ORCHESTRATOR NODE
# ============================================================================

async def orchestrator_node(state: AgentState) -> AgentState:
    """
    Master orchestrator that decides which agents to call
    """
    request = state["current_request"].lower()
    agents_needed = []
    
    # Intent detection based on keywords
    if any(word in request for word in ["recommend", "suggest", "show", "match", "pair", "goes with"]):
        agents_needed.append("recommendation")
    
    if any(word in request for word in ["stock", "available", "store", "nearby", "reserve"]):
        agents_needed.append("inventory")
    
    if any(word in request for word in ["pay", "payment", "checkout", "buy", "purchase"]):
        agents_needed.append("payment")
        
    if any(word in request for word in ["deliver", "shipping", "delivery", "when will"]):
        agents_needed.append("fulfillment")
    
    if any(word in request for word in ["discount", "offer", "points", "loyalty", "coupon"]):
        agents_needed.append("loyalty")
    
    if any(word in request for word in ["return", "refund", "exchange", "problem", "issue", "help"]):
        agents_needed.append("support")
    
    # Default: if cart or liked products exist, also call recommendation
    if state.get("cart") or state.get("liked_products"):
        if "recommendation" not in agents_needed:
            agents_needed.append("recommendation")
    
    # Always include loyalty to check for applicable offers
    if "loyalty" not in agents_needed and len(agents_needed) > 0:
        agents_needed.append("loyalty")
    
    state["agents_needed"] = agents_needed
    state["agent_calls"].append({
        "agent": "orchestrator",
        "action": "analyzed_request",
        "agents_to_call": agents_needed
    })
    
    return state

# ============================================================================
# ROUTING LOGIC
# ============================================================================

def should_call_agents(state: AgentState) -> str:
    """
    Decide if we need to call specialized agents
    """
    if state.get("agents_needed"):
        return "call_agents"
    else:
        return "simple_response"

# ============================================================================
# AGENT CALLER NODE (Parallel Execution)
# ============================================================================

async def call_agents_node(state: AgentState) -> AgentState:
    """
    Call all needed agents in parallel
    """
    agents_needed = state.get("agents_needed", [])
    
    # Create tasks for parallel execution
    tasks = []
    
    if "recommendation" in agents_needed:
        tasks.append(recommendation_agent.run(state))
    
    if "inventory" in agents_needed:
        tasks.append(inventory_agent.run(state))
    
    if "payment" in agents_needed:
        tasks.append(payment_agent.run(state))
    
    if "fulfillment" in agents_needed:
        tasks.append(fulfillment_agent.run(state))
    
    if "loyalty" in agents_needed:
        tasks.append(loyalty_agent.run(state))
    
    if "support" in agents_needed:
        tasks.append(support_agent.run(state))
    
    # Execute all agents in parallel
    if tasks:
        results = await asyncio.gather(*tasks)
        
        # Merge results back into state
        for result in results:
            if result:
                state.update(result)
    
    return state

# ============================================================================
# RESPONSE SYNTHESIS NODE
# ============================================================================

async def synthesize_response_node(state: AgentState) -> AgentState:
    """
    Combine all agent responses into a coherent reply
    """
    response_parts = []
    
    # Greeting
    if not state.get("messages"):
        response_parts.append("Hi! I'm your AI shopping assistant. How can I help you today?")
    
    # Recommendations
    if state.get("recommendations"):
        recs = state["recommendations"]
        response_parts.append(f"Based on your preferences, I found {len(recs)} items you might love:")
        for rec in recs[:3]:  # Top 3
            response_parts.append(f"• {rec['name']} - ₹{rec['price']}")
    
    # Inventory status
    if state.get("inventory_status"):
        inv = state["inventory_status"]
        if inv.get("available"):
            response_parts.append(f"✓ Available at {inv['store']} ({inv['stock']} in stock)")
        else:
            response_parts.append(f"Currently unavailable. Alternative: {inv.get('alternative', 'Check other stores')}")
    
    # Loyalty offers
    if state.get("loyalty_info"):
        loyalty = state["loyalty_info"]
        if loyalty.get("points_available"):
            response_parts.append(f"💎 You have {loyalty['points_available']} loyalty points (₹{loyalty['value']})")
        if loyalty.get("offers"):
            response_parts.append(f"🎁 Special offer: {loyalty['offers'][0]}")
    
    # Payment status
    if state.get("payment_status"):
        payment = state["payment_status"]
        if payment.get("success"):
            response_parts.append(f"✅ Payment successful! Transaction ID: {payment['transaction_id']}")
        else:
            response_parts.append(f"⚠️ Payment issue: {payment.get('message', 'Please try again')}")
    
    # Fulfillment info
    if state.get("fulfillment_info"):
        fulfillment = state["fulfillment_info"]
        response_parts.append(f"📦 Delivery: {fulfillment.get('timeline', '2-3 days')}")
    
    # Support info
    if state.get("support_info"):
        support = state["support_info"]
        response_parts.append(support.get("message", ""))
    
    # Default response if no specific info
    if not response_parts:
        response_parts.append("I'm here to help! You can ask me about products, check availability, or place an order.")
    
    state["response"] = "\n\n".join(response_parts)
    return state

# ============================================================================
# SIMPLE RESPONSE NODE (No agents needed)
# ============================================================================

async def simple_response_node(state: AgentState) -> AgentState:
    """
    Handle simple queries without calling agents
    """
    request = state["current_request"].lower()
    
    # Greeting responses
    if any(word in request for word in ["hi", "hello", "hey"]):
        state["response"] = "Hello! I'm your AI shopping assistant. I can help you find products, check availability, and complete your purchase. What are you looking for today?"
    
    # Thank you
    elif any(word in request for word in ["thank", "thanks"]):
        state["response"] = "You're welcome! Is there anything else I can help you with?"
    
    # Default
    else:
        state["response"] = "I'm here to help! You can ask me about products, availability, or placing an order."
    
    return state

# ============================================================================
# CREATE THE GRAPH
# ============================================================================

def create_orchestrator_graph():
    """
    Build the LangGraph workflow
    """
    # Create graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("call_agents", call_agents_node)
    workflow.add_node("simple_response", simple_response_node)
    workflow.add_node("synthesize", synthesize_response_node)
    
    # Set entry point
    workflow.set_entry_point("orchestrator")
    
    # Add conditional routing
    workflow.add_conditional_edges(
        "orchestrator",
        should_call_agents,
        {
            "call_agents": "call_agents",
            "simple_response": "simple_response"
        }
    )
    
    # Agent caller goes to synthesizer
    workflow.add_edge("call_agents", "synthesize")
    
    # Simple response goes to synthesizer
    workflow.add_edge("simple_response", "synthesize")
    
    # Synthesizer ends
    workflow.add_edge("synthesize", END)
    
    # Compile the graph
    return workflow.compile()

# ============================================================================
# GRAPH VISUALIZATION (for debugging)
# ============================================================================

def visualize_graph():
    """
    Print the graph structure
    """
    graph = create_orchestrator_graph()
    print("=== AI Orchestrator Graph ===")
    print("Nodes:", graph.nodes)
    print("Edges:", graph.edges)
    return graph