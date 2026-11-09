"""The active agents. To add an agent, create its file and add it to this list."""

from ai_workflow.agents.fulfillment_agent import FulfillmentAgent
from ai_workflow.agents.inventory_agent import InventoryAgent
from ai_workflow.agents.loyalty_agent import LoyaltyAgent
from ai_workflow.agents.payment_agent import PaymentAgent
from ai_workflow.agents.recommendation_agent import RecommendationAgent
from ai_workflow.agents.support_agent import SupportAgent

AGENTS = {
    agent.name: agent
    for agent in [
        RecommendationAgent(),
        InventoryAgent(),
        PaymentAgent(),
        FulfillmentAgent(),
        LoyaltyAgent(),
        SupportAgent(),
    ]
}
