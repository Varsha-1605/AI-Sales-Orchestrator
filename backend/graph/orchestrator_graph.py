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
# SALES PSYCHOLOGY PROMPTS
# ============================================================================

SALES_PERSONALITY = """
You are a top-tier sales associate at Van Heusen - warm, knowledgeable, and genuinely helpful.

KEY PRINCIPLES:
1. ASK DISCOVERY QUESTIONS - Understand before recommending
2. USE EMOTIONAL LANGUAGE - "You'll look sharp", "Perfect for making impressions"
3. HANDLE OBJECTIONS WITH EMPATHY - Never pushy, always understanding
4. CREATE URGENCY (HONESTLY) - "Only 3 left", "Back in stock"
5. SOCIAL PROOF - "250+ customers loved this"
6. ASSUMPTIVE CLOSE - "Should I add this to your cart?"

TONE: Friendly, confident, consultative (not salesy or robotic)
"""

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
# RESPONSE SYNTHESIS NODE (WITH SALES PSYCHOLOGY)
# ============================================================================

async def synthesize_response_node(state: AgentState) -> AgentState:
    """
    Combine all agent responses into a consultative sales conversation
    """
    response_parts = []
    
    # Recommendations (Sales-oriented with reasoning)
    if state.get("recommendations"):
        recs = state["recommendations"]
        
        # SALES PSYCHOLOGY: Emotional opening
        response_parts.append(f"I found {len(recs)} items that would look amazing on you! 🎯\n")
        
        for rec in recs[:3]:
            # SALES PSYCHOLOGY: Name + Price + Reasoning + Social Proof
            reasoning = rec.get('reasoning', 'Perfect for your style')
            social_proof = rec.get('social_proof', 'Customer favorite')
            
            response_parts.append(
                f"✨ **{rec['name']}** (₹{rec['price']})\n"
                f"   💡 Why I picked this: {reasoning}\n"
                f"   👥 {social_proof}\n"
            )
        
        # SALES PSYCHOLOGY: Assumptive close with follow-up question
        response_parts.append("\nWhich style catches your eye? I can check store availability! 😊")
    
    # Inventory status (Consultative)
    if state.get("inventory_status"):
        inv = state["inventory_status"]
        if inv.get("available"):
            # SALES PSYCHOLOGY: Create urgency
            stock = inv.get('stock', 5)
            urgency = ""
            if stock <= 3:
                urgency = f"⚡ Only {stock} left - "
            
            response_parts.append(
                f"\n{urgency}✅ Available at {inv.get('store', 'your location')} "
                f"({inv.get('distance', '2km')} away)\n"
                f"Want me to reserve this for you? You can try it on today!"
            )
        else:
            # SALES PSYCHOLOGY: Recovery with alternatives
            response_parts.append(
                f"\n❌ Unfortunately unavailable at your location.\n\n"
                f"But don't worry! I found:\n"
                f"✓ Similar items at nearby stores\n"
                f"✓ Alternative products you'll love\n\n"
                f"Want to see options?"
            )
    
    # Loyalty offers (Value proposition)
    if state.get("loyalty_info"):
        loyalty = state["loyalty_info"]
        if loyalty.get("points_available"):
            # SALES PSYCHOLOGY: Emphasize savings
            points = loyalty['points_available']
            value = loyalty.get('points_value', points)
            response_parts.append(
                f"\n💎 Great news! You have **{points} loyalty points** (₹{value} value)\n"
                f"I can apply these to save you money!"
            )
        if loyalty.get("offers"):
            # SALES PSYCHOLOGY: Create excitement about offers
            offer = loyalty['offers'][0] if isinstance(loyalty['offers'], list) else loyalty['offers']
            response_parts.append(f"\n🎁 **Special offer:** {offer}")
    
    # Payment status (Reassurance)
    if state.get("payment_status"):
        payment = state["payment_status"]
        if payment.get("success"):
            response_parts.append(
                f"\n🎉 **Order confirmed!**\n"
                f"Transaction ID: {payment.get('transaction_id', 'N/A')}\n"
                f"You'll receive tracking details shortly!"
            )
        else:
            response_parts.append(
                f"\n⚠️ Payment issue: {payment.get('message', 'Please try again')}\n"
                f"Don't worry - your cart is saved!"
            )
    
    # Fulfillment info (Build anticipation)
    if state.get("fulfillment_info"):
        fulfillment = state["fulfillment_info"]
        timeline = fulfillment.get('timeline', '2-3 days')
        response_parts.append(
            f"\n📦 **Delivery:** {timeline}\n"
            f"Track your order anytime in the app!"
        )
    
    # Support info
    if state.get("support_info"):
        support = state["support_info"]
        response_parts.append(f"\n{support.get('message', '')}")
    
    # Default response if no specific info (Discovery question)
    if not response_parts:
        response_parts.append(
            "I'm here to help you find the perfect outfit! 😊\n\n"
            "What are you shopping for today?"
        )
    
    state["response"] = "\n".join(response_parts)
    return state



# ============================================================================
# SIMPLE RESPONSE NODE (With Sales Personality)
# ============================================================================

async def simple_response_node(state: AgentState) -> AgentState:
    """
    Handle simple queries with sales personality
    """
    request = state["current_request"].lower()
    
    # Greeting responses (Warm and inviting)
    if any(word in request for word in ["hi", "hello", "hey"]):
        state["response"] = (
            "Hello! Great to see you! 👋\n\n"
            "I'm your personal shopping assistant at Van Heusen. "
            "I'm here to help you find outfits that make you look and feel amazing!\n\n"
            "What brings you here today?"
        )
    
    # Thank you (Build relationship)
    elif any(word in request for word in ["thank", "thanks"]):
        state["response"] = (
            "You're very welcome! 😊\n\n"
            "I'm always here if you need anything else. "
            "Happy shopping!"
        )
    
    # Default (Discovery question)
    else:
        state["response"] = (
            "I'd love to help you with that! 😊\n\n"
            "To find the perfect items for you, could you tell me:\n"
            "• What's the occasion?\n"
            "• Any colors you prefer?\n"
            "• What's your budget range?"
        )
    
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