"""
Recommendation Agent
Handles product suggestions, matching, and styling
"""

from agents.base_agent import BaseAgent
from typing import Dict, Any, List
import json

class RecommendationAgent(BaseAgent):
    
    def __init__(self):
        super().__init__(
            agent_name="Recommendation Agent",
            agent_description="Suggests products based on customer preferences and browsing history"
        )
        # Load product catalog
        self.products = self._load_products()
    
    def _load_products(self) -> List[Dict[str, Any]]:
        """Load product catalog"""
        try:
            with open("data/products.json", 'r') as f:
                data = json.load(f)
                return data.get("products", [])
        except:
            # Fallback mock products
            return [
                {
                    "product_id": "VH001",
                    "name": "Classic Blue Formal Shirt",
                    "brand": "Van Heusen",
                    "price": 2500,
                    "category": "Formal Shirts",
                    "tags": ["wedding", "formal", "office"],
                    "match_score": 0.95
                },
                {
                    "product_id": "VH002",
                    "name": "Navy Blue Silk Tie",
                    "brand": "Van Heusen",
                    "price": 800,
                    "category": "Ties",
                    "tags": ["formal", "wedding"],
                    "match_score": 0.85
                },
                {
                    "product_id": "VH003",
                    "name": "Brown Leather Belt",
                    "brand": "Van Heusen",
                    "price": 1200,
                    "category": "Belts",
                    "tags": ["formal", "casual"],
                    "match_score": 0.78
                }
            ]
    
    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate product recommendations
        """
        liked_products = state.get("liked_products", [])
        cart = state.get("cart", [])
        request = state.get("current_request", "").lower()
        
        recommendations = []
        
        # If customer has liked products, suggest matching items
        if liked_products:
            recommendations = self._get_matching_products(liked_products)
        
        # If cart has items, suggest complementary products
        elif cart:
            recommendations = self._get_complementary_products(cart)
        
        # Default recommendations
        else:
            recommendations = self._get_trending_products()
        
        # Add reasoning for each recommendation
        for rec in recommendations:
            rec["reasoning"] = self._generate_reasoning(rec, state)
        
        return {
            "recommendations": recommendations[:5],  # Top 5
            "total_found": len(recommendations)
        }
    
    def _get_matching_products(self, liked_product_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Find products that match with liked items
        """
        # In real implementation, use ML model or collaborative filtering
        # For demo, return complementary categories
        
        matched = []
        for product in self.products:
            # If customer liked shirts, suggest ties and belts
            if any(pid.startswith("VH") for pid in liked_product_ids):
                if product["category"] in ["Ties", "Belts", "Trousers"]:
                    matched.append(product)
        
        return matched or self.products[:3]
    
    def _get_complementary_products(self, cart: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Suggest products that complement cart items
        """
        # Similar logic to matching
        return self._get_matching_products([item["product_id"] for item in cart])
    
    def _get_trending_products(self) -> List[Dict[str, Any]]:
        """
        Return trending/popular products
        """
        return sorted(self.products, key=lambda x: x.get("match_score", 0), reverse=True)
    
    def _generate_reasoning(self, product: Dict[str, Any], state: Dict[str, Any]) -> str:
        """
        Generate explanation for why this product is recommended
        """
        if state.get("liked_products"):
            return f"Pairs perfectly with your liked items"
        elif state.get("cart"):
            return f"Completes your look"
        else:
            return f"Popular choice for {', '.join(product.get('tags', [])[:2])}"