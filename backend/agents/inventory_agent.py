"""
Inventory Agent
Handles stock checking, store location, and reservations
"""

from agents.base_agent import BaseAgent
from typing import Dict, Any, List
import json

class InventoryAgent(BaseAgent):
    
    def __init__(self):
        super().__init__(
            agent_name="Inventory Agent",
            agent_description="Checks stock availability and finds alternative locations"
        )
        self.stores = self._load_stores()
        self.products = self._load_products()
    
    def _load_stores(self) -> List[Dict[str, Any]]:
        """Load store locations"""
        try:
            with open("data/stores.json", 'r') as f:
                data = json.load(f)
                return data.get("stores", [])
        except:
            return [
                {"store_id": "S001", "name": "Bandra Store", "location": "Mumbai", "distance": "2km"},
                {"store_id": "S002", "name": "Powai Store", "location": "Mumbai", "distance": "5km"},
                {"store_id": "S003", "name": "Andheri Store", "location": "Mumbai", "distance": "7km"}
            ]
    
    def _load_products(self) -> Dict[str, Any]:
        """Load product inventory"""
        try:
            with open("data/products.json", 'r') as f:
                data = json.load(f)
                products_dict = {}
                for p in data.get("products", []):
                    products_dict[p["product_id"]] = p
                return products_dict
        except:
            return {}
    
    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check inventory and provide alternatives
        """
        request = state.get("current_request", "").lower()
        cart = state.get("cart", [])
        location = state.get("location", "Mumbai")
        
        # Determine what to check
        if "stock" in request or "available" in request:
            # Check specific product from cart or request
            if cart:
                product_id = cart[0]["product_id"]
                size = cart[0].get("size", "40")
            else:
                product_id = "VH001"  # Default
                size = "40"
            
            return await self._check_stock(product_id, size, location)
        
        elif "store" in request or "nearby" in request:
            # Find nearby stores
            return self._find_nearby_stores(location)
        
        else:
            # Default: check if cart items are available
            if cart:
                return await self._check_cart_availability(cart, location)
            else:
                return {"available": True, "message": "All items in stock"}
    
    async def _check_stock(self, product_id: str, size: str, location: str) -> Dict[str, Any]:
        """
        Check stock for specific product and size
        """
        # Simulate different scenarios for demo
        
        # Scenario 1: In stock at current location
        if product_id == "VH001":
            return {
                "available": True,
                "product_id": product_id,
                "size": size,
                "store": "Bandra Store",
                "stock": 3,
                "distance": "2km",
                "can_reserve": True
            }
        
        # Scenario 2: Out of stock - show alternatives (EDGE CASE)
        elif product_id == "VH999" or "out" in product_id.lower():
            nearby_stores = self._find_nearby_stores(location)
            alternatives = self._find_alternative_products(product_id)
            
            return {
                "available": False,
                "product_id": product_id,
                "size": size,
                "message": f"Size {size} unavailable at your location",
                "nearby_stores": nearby_stores[:2],
                "alternatives": alternatives[:2],
                "restock_date": "3 days"
            }
        
        # Default: Available
        else:
            return {
                "available": True,
                "product_id": product_id,
                "size": size,
                "store": "Bandra Store",
                "stock": 5,
                "distance": "2km"
            }
    
    async def _check_cart_availability(self, cart: List[Dict], location: str) -> Dict[str, Any]:
        """
        Check if all cart items are available
        """
        all_available = True
        unavailable_items = []
        
        for item in cart:
            stock_info = await self._check_stock(
                item["product_id"],
                item.get("size", "40"),
                location
            )
            
            if not stock_info.get("available"):
                all_available = False
                unavailable_items.append(item["product_id"])
        
        return {
            "all_available": all_available,
            "unavailable_items": unavailable_items,
            "message": "All items available" if all_available else "Some items unavailable"
        }
    
    def _find_nearby_stores(self, location: str) -> List[Dict[str, Any]]:
        """
        Find stores near customer location
        """
        # Sort by distance (mock)
        stores_with_stock = []
        for store in self.stores:
            stores_with_stock.append({
                "name": store["name"],
                "distance": store["distance"],
                "stock_available": True,
                "stock_count": 3  # Mock
            })
        
        return stores_with_stock
    
    def _find_alternative_products(self, product_id: str) -> List[Dict[str, Any]]:
        """
        Find similar products as alternatives
        """
        # Return similar products
        alternatives = []
        for pid, product in self.products.items():
            if pid != product_id:
                alternatives.append({
                    "product_id": pid,
                    "name": product.get("name", "Alternative Product"),
                    "price": product.get("price", 2500),
                    "similarity": 0.85
                })
                if len(alternatives) >= 3:
                    break
        
        return alternatives