"""
Recommendation Agent
Handles product suggestions, matching, and styling
"""

import asyncio
from typing import Any, Dict, List

from ai_workflow.agents.base_agent import BaseAgent
from ai_workflow.storage import catalog_store
from ai_workflow.tools.catalog import find_matching_products

MAX_RECOMMENDATIONS = 5


class RecommendationAgent(BaseAgent):
    name = "recommendation"
    description = "Suggests products based on customer preferences and browsing history"
    result_key = "recommendations"
    system_prompt = (
        "You are a Van Heusen sales associate. Write one short, friendly line (under 15 words) "
        "saying why a product suits the customer. Reply with that line only."
    )

    async def _execute(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate product recommendations
        """
        liked_products = state.get("liked_products", [])
        cart = state.get("cart", [])

        if liked_products:
            recommendations = find_matching_products(liked_products)
        elif cart:
            recommendations = find_matching_products([item["product_id"] for item in cart])
        else:
            recommendations = self._get_trending_products()

        top = recommendations[:MAX_RECOMMENDATIONS]
        reasons = await asyncio.gather(*(self._generate_reasoning(rec, state) for rec in top))
        for rec, reason in zip(top, reasons):
            rec["reasoning"] = reason
        return top

    def _get_trending_products(self) -> List[Dict[str, Any]]:
        """
        Return trending/popular products
        """
        products = [dict(p) for p in catalog_store.list_products()]
        return sorted(products, key=lambda x: x.get("match_score", 0), reverse=True)

    async def _generate_reasoning(self, product: Dict[str, Any], state: Dict[str, Any]) -> str:
        """
        Explain why this product is recommended. Uses Claude when a key is set, else a template.
        """
        if state.get("liked_products"):
            template = "Pairs perfectly with your liked items"
        elif state.get("cart"):
            template = "Completes your look"
        else:
            template = f"Popular choice for {', '.join(product.get('tags', [])[:2])}"

        prompt = (
            f"Product: {product['name']} ({product['category']}, tags: {', '.join(product.get('tags', []))}).\n"
            f"Customer liked: {state.get('liked_products', [])}. Cart: {[i['product_id'] for i in state.get('cart', [])]}.\n"
            f"Customer said: {state.get('current_request', '')}"
        )
        return (await self._call_llm(prompt, fallback=template)).strip()
