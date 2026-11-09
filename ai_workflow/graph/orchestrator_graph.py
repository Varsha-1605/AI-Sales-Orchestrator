"""
LangGraph Multi-Agent Orchestrator
Coordinates all 6 specialized agents
"""

import asyncio
from typing import Any, Dict

from langgraph.graph import StateGraph, END

from ai_workflow.agents import AGENTS
from ai_workflow.graph.approval import ask_for_approval
from ai_workflow.graph.state import AgentState
from ai_workflow.graph.supervisor import choose_agents
from ai_workflow.guardrails import run_input_checks

BLOCKED_REPLY = (
    "I can only help with shopping at Van Heusen - products, stock, offers, orders and support. "
    "What are you looking for today?"
)

# ============================================================================
# INPUT CHECK NODE
# ============================================================================

def check_input_node(state: AgentState) -> Dict[str, Any]:
    """
    Stop messages that fail the input checks before any agent sees them
    """
    blocked, reason = run_input_checks(state["current_request"])
    if blocked:
        return {"blocked": True, "response": BLOCKED_REPLY, "error": reason}
    return {"blocked": False}

# ============================================================================
# ORCHESTRATOR NODE
# ============================================================================

async def orchestrator_node(state: AgentState) -> Dict[str, Any]:
    """
    Master orchestrator that decides which agents to call
    """
    agents_needed = await choose_agents(state)
    return {
        "agents_needed": agents_needed,
        "agent_calls": state["agent_calls"] + [{
            "agent": "orchestrator",
            "action": "analyzed_request",
            "agents_to_call": agents_needed
        }],
    }

# ============================================================================
# ROUTING LOGIC
# ============================================================================

def after_input_check(state: AgentState) -> str:
    return END if state["blocked"] else "orchestrator"


def should_call_agents(state: AgentState) -> str:
    """
    Decide if we need to call specialized agents
    """
    if state.get("agents_needed"):
        return "ask_for_approval"
    else:
        return "simple_response"


def after_approval(state: AgentState) -> str:
    """
    If the customer said no, there may be nothing left to run
    """
    return "call_agents" if state["agents_needed"] else "synthesize"

# ============================================================================
# AGENT CALLER NODE (Parallel Execution)
# ============================================================================

async def call_agents_node(state: AgentState) -> Dict[str, Any]:
    """
    Call all needed agents in parallel and keep each result under its own key
    """
    results = await asyncio.gather(*(AGENTS[name].run(state) for name in state["agents_needed"]))

    update: Dict[str, Any] = {}
    agent_calls = list(state["agent_calls"])
    for result in results:
        for key, value in result.items():
            if key == "agent_calls":
                agent_calls.extend(value)
            else:
                update[key] = value
    update["agent_calls"] = agent_calls
    return update

# ============================================================================
# RESPONSE SYNTHESIS NODE (WITH SALES PSYCHOLOGY)
# ============================================================================

async def synthesize_response_node(state: AgentState) -> Dict[str, Any]:
    """
    Combine all agent responses into a consultative sales conversation
    """
    response_parts = []

    # Customer said no to the payment
    if state.get("next_action") == "payment_cancelled":
        response_parts.append("No problem - I've cancelled the payment. Your cart is saved!")

    # Recommendations (Sales-oriented with reasoning)
    if state.get("recommendations"):
        recs = state["recommendations"]

        # SALES PSYCHOLOGY: Emotional opening
        response_parts.append(f"I found {len(recs)} items that would look amazing on you!\n")

        for rec in recs[:3]:
            # SALES PSYCHOLOGY: Name + Price + Reasoning + Social Proof
            reasoning = rec.get('reasoning', 'Perfect for your style')
            social_proof = rec.get('social_proof', 'Customer favorite')

            response_parts.append(
                f"{rec['name']} (₹{rec['price']})\n"
                f"   Why I picked this: {reasoning}\n"
                f"   {social_proof}\n"
            )

        # SALES PSYCHOLOGY: Assumptive close with follow-up question
        response_parts.append("\nWhich style catches your eye? I can check store availability!")

    # Inventory status (Consultative)
    if state.get("inventory_status"):
        inv = state["inventory_status"]
        if inv.get("available"):
            # SALES PSYCHOLOGY: Create urgency
            stock = inv.get('stock', 5)
            urgency = ""
            if stock <= 3:
                urgency = f"Only {stock} left - "

            response_parts.append(
                f"\n{urgency}Available at {inv.get('store', 'your location')} "
                f"({inv.get('distance', '2km')} away)\n"
                f"Want me to reserve this for you? You can try it on today!"
            )
        else:
            # SALES PSYCHOLOGY: Recovery with alternatives
            response_parts.append(
                f"\nUnfortunately unavailable at your location.\n\n"
                f"But don't worry! I found:\n"
                f"- Similar items at nearby stores\n"
                f"- Alternative products you'll love\n\n"
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
                f"\nGreat news! You have {points} loyalty points (₹{value} value)\n"
                f"I can apply these to save you money!"
            )
        if loyalty.get("offers"):
            # SALES PSYCHOLOGY: Create excitement about offers
            offer = loyalty['offers'][0] if isinstance(loyalty['offers'], list) else loyalty['offers']
            response_parts.append(f"\nSpecial offer: {offer}")

    # Payment status (Reassurance)
    if state.get("payment_status"):
        payment = state["payment_status"]
        if payment.get("success"):
            response_parts.append(
                f"\nOrder confirmed!\n"
                f"Transaction ID: {payment.get('transaction_id', 'N/A')}\n"
                f"You'll receive tracking details shortly!"
            )
        else:
            response_parts.append(
                f"\nPayment issue: {payment.get('message', 'Please try again')}\n"
                f"Don't worry - your cart is saved!"
            )

    # Fulfillment info (Build anticipation)
    if state.get("fulfillment_info"):
        fulfillment = state["fulfillment_info"]
        timeline = fulfillment.get('timeline', '2-3 days')
        response_parts.append(
            f"\nDelivery: {timeline}\n"
            f"Track your order anytime in the app!"
        )

    # Support info
    if state.get("support_info"):
        support = state["support_info"]
        response_parts.append(f"\n{support.get('message', '')}")

    # Default response if no specific info (Discovery question)
    if not response_parts:
        response_parts.append(
            "I'm here to help you find the perfect outfit!\n\n"
            "What are you shopping for today?"
        )

    return {"response": "\n".join(response_parts)}

# ============================================================================
# SIMPLE RESPONSE NODE (With Sales Personality)
# ============================================================================

async def simple_response_node(state: AgentState) -> Dict[str, Any]:
    """
    Handle simple queries with sales personality
    """
    request = state["current_request"].lower()

    # Greeting responses (Warm and inviting)
    if any(word in request for word in ["hi", "hello", "hey"]):
        response = (
            "Hello! Great to see you!\n\n"
            "I'm your personal shopping assistant at Van Heusen. "
            "I'm here to help you find outfits that make you look and feel amazing!\n\n"
            "What brings you here today?"
        )

    # Thank you (Build relationship)
    elif any(word in request for word in ["thank", "thanks"]):
        response = (
            "You're very welcome!\n\n"
            "I'm always here if you need anything else. "
            "Happy shopping!"
        )

    # Default (Discovery question)
    else:
        response = (
            "I'd love to help you with that!\n\n"
            "To find the perfect items for you, could you tell me:\n"
            "• What's the occasion?\n"
            "• Any colors you prefer?\n"
            "• What's your budget range?"
        )

    return {"response": response}

# ============================================================================
# CREATE THE GRAPH
# ============================================================================

def create_orchestrator_graph(checkpointer):
    """
    Build the LangGraph workflow. Use the session id as the thread id when calling it.
    """
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("check_input", check_input_node)
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("ask_for_approval", ask_for_approval)
    workflow.add_node("call_agents", call_agents_node)
    workflow.add_node("simple_response", simple_response_node)
    workflow.add_node("synthesize", synthesize_response_node)

    # Set entry point
    workflow.set_entry_point("check_input")

    # Blocked messages end here with a safe reply
    workflow.add_conditional_edges(
        "check_input",
        after_input_check,
        {"orchestrator": "orchestrator", END: END}
    )

    # Add conditional routing
    workflow.add_conditional_edges(
        "orchestrator",
        should_call_agents,
        {
            "ask_for_approval": "ask_for_approval",
            "simple_response": "simple_response"
        }
    )
    workflow.add_conditional_edges(
        "ask_for_approval",
        after_approval,
        {"call_agents": "call_agents", "synthesize": "synthesize"}
    )

    # Agent caller goes to synthesizer
    workflow.add_edge("call_agents", "synthesize")

    # Greetings and thanks already have their reply
    workflow.add_edge("simple_response", END)

    # Synthesizer ends
    workflow.add_edge("synthesize", END)

    return workflow.compile(checkpointer=checkpointer)
