"""Product search, matching products and stock lookups."""

from typing import Any, Dict, List, Optional

from ai_workflow.storage import catalog_store

SHIRT_CATEGORY = "Formal Shirts"
SHIRT_PARTNER_CATEGORIES = ["Ties", "Belts", "Trousers"]
MATCHING_FALLBACK_COUNT = 3
ALTERNATIVE_COUNT = 2
RESTOCK_TIME = "3 days"


def search_products(
    query: Optional[str] = None,
    category: Optional[str] = None,
    color: Optional[str] = None,
    max_price: Optional[float] = None,
) -> List[Dict[str, Any]]:
    words = (query or "").lower().split()
    found = []
    for product in catalog_store.list_products(category):
        text = " ".join([product["name"], product["category"], *product["tags"], *product["colors"]]).lower()
        if not all(word in text for word in words):
            continue
        if color and not any(color.lower() in c.lower() for c in product["colors"]):
            continue
        if max_price is not None and product["price"] > max_price:
            continue
        found.append(dict(product))
    return sorted(found, key=lambda p: p.get("match_score", 0), reverse=True)


def find_matching_products(product_ids: List[str]) -> List[Dict[str, Any]]:
    """Ties, belts and trousers for shirts, same color first. Top products when nothing matches."""
    seeds = [p for p in map(catalog_store.get_product, product_ids) if p]
    if any(p["category"] == SHIRT_CATEGORY for p in seeds):
        seed_colors = {c for p in seeds for c in p["colors"]}
        matches = [
            dict(p) for p in catalog_store.list_products() if p["category"] in SHIRT_PARTNER_CATEGORIES
        ]
        matches.sort(key=lambda p: (not seed_colors.intersection(p["colors"]), -p.get("match_score", 0)))
        return matches
    ranked = sorted(catalog_store.list_products(), key=lambda p: p.get("match_score", 0), reverse=True)
    return [dict(p) for p in ranked[:MATCHING_FALLBACK_COUNT]]


def nearby_stores(location: str) -> List[Dict[str, Any]]:
    """Stores in the customer's city, or all stores when none match."""
    stores = catalog_store.list_stores()
    in_city = [s for s in stores if s["location"].lower() in location.lower()]
    return in_city or stores


def check_stock(product_id: str, size: str, location: str) -> Dict[str, Any]:
    """Stock in nearby stores. Adds alternatives and a restock estimate when nothing is in stock."""
    stores = [
        {"name": s["name"], "distance": s["distance"], "stock": catalog_store.get_stock(product_id, s["name"], size)}
        for s in nearby_stores(location)
    ]
    best = next((s for s in stores if s["stock"] > 0), None)
    if best:
        return {
            "available": True,
            "product_id": product_id,
            "size": size,
            "store": best["name"],
            "stock": best["stock"],
            "distance": best["distance"],
            "can_reserve": True,
            "stores": stores,
        }
    return {
        "available": False,
        "product_id": product_id,
        "size": size,
        "message": f"Size {size} unavailable at your location",
        "stores": stores,
        "alternatives": _alternatives(product_id)[:ALTERNATIVE_COUNT],
        "restock_date": RESTOCK_TIME,
    }


def _alternatives(product_id: str) -> List[Dict[str, Any]]:
    product = catalog_store.get_product(product_id)
    category = product["category"] if product else None
    return [
        {"product_id": p["product_id"], "name": p["name"], "price": p["price"]}
        for p in catalog_store.list_products(category)
        if p["product_id"] != product_id and catalog_store.is_in_stock(p["product_id"])
    ]
