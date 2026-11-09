"""Picks which agents should handle a customer message."""

from typing import Any, Dict, List

from loguru import logger
from pydantic import BaseModel

from ai_workflow.agents import AGENTS
from ai_workflow.llm import build_llm

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

KEYWORDS = {
    "recommendation": ["recommend", "suggest", "show", "match", "pair", "goes with"],
    "inventory": ["stock", "available", "store", "nearby", "reserve"],
    "payment": ["pay", "payment", "checkout", "buy", "purchase"],
    "fulfillment": ["deliver", "shipping", "delivery", "when will"],
    "loyalty": ["discount", "offer", "points", "loyalty", "coupon"],
    "support": ["return", "refund", "exchange", "problem", "issue", "help"],
}


class AgentChoice(BaseModel):
    agents: List[str]


llm = build_llm(temperature=0, max_tokens=200)


async def choose_agents(state: Dict[str, Any]) -> List[str]:
    """Agent names for this message: asks Claude when a key is set, else uses keyword rules."""
    agents_needed = await _choose_with_llm(state) if llm else None
    if agents_needed is None:
        agents_needed = _choose_with_keywords(state)

    # Always include loyalty to check for applicable offers
    if "loyalty" not in agents_needed and len(agents_needed) > 0:
        agents_needed.append("loyalty")
    return agents_needed


async def _choose_with_llm(state: Dict[str, Any]) -> List[str] | None:
    agent_list = "\n".join(f"- {name}: {agent.description}" for name, agent in AGENTS.items())
    system_prompt = (
        f"{SALES_PERSONALITY}\n"
        "Decide which specialist agents are needed for the customer's message. "
        f"Choose only from this list, or return an empty list for a greeting or small talk:\n{agent_list}"
    )
    message = f"Cart has items: {bool(state.get('cart'))}\nCustomer message: {state['current_request']}"
    try:
        choice = await llm.with_structured_output(AgentChoice).ainvoke([("system", system_prompt), ("user", message)])
    except Exception as e:
        logger.error("LLM routing failed, using keyword rules: {}", e)
        return None
    return [name for name in choice.agents if name in AGENTS]


def _choose_with_keywords(state: Dict[str, Any]) -> List[str]:
    request = state["current_request"].lower()
    agents_needed = [name for name, words in KEYWORDS.items() if any(word in request for word in words)]

    # Default: if cart or liked products exist, also call recommendation
    if state.get("cart") or state.get("liked_products"):
        if "recommendation" not in agents_needed:
            agents_needed.append("recommendation")
    return agents_needed
