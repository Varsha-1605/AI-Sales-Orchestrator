"""Read-only product, store and customer data from the JSON files in DATA_DIR."""

import json
from functools import cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_workflow.settings import settings


@cache
def _load(file_name: str, key: str) -> List[Dict[str, Any]]:
    path = Path(settings.DATA_DIR) / file_name
    with open(path, encoding="utf-8") as file:
        return json.load(file)[key]


def preload() -> Dict[str, int]:
    """Read all three data files now instead of on the first request. Fails at startup if one is missing."""
    return {
        "products": len(_load("products.json", "products")),
        "stores": len(_load("stores.json", "stores")),
        "customers": len(_load("customers.json", "customers")),
    }


def get_product(product_id: str) -> Optional[Dict[str, Any]]:
    for product in _load("products.json", "products"):
        if product["product_id"] == product_id:
            return product
    return None


def list_products(category: Optional[str] = None) -> List[Dict[str, Any]]:
    products = _load("products.json", "products")
    if category:
        return [p for p in products if p["category"] == category]
    return list(products)


def get_stock(product_id: str, store: str, size: str) -> int:
    """Units in stock. The inventory uses short names ("Bandra"), stores use "Bandra Store"."""
    product = get_product(product_id)
    if not product:
        return 0
    short_name = store.removesuffix(" Store")
    if size not in product["sizes"]:
        # Ties, socks and belts do not come in the shirt size the pages send ("40"): use the product's first size
        size = product["sizes"][0]
    return product.get("inventory", {}).get(short_name, {}).get(size, 0)


def is_in_stock(product_id: str) -> bool:
    """True when any store has at least one unit in any size."""
    product = get_product(product_id)
    if not product:
        return False
    return any(units > 0 for sizes in product.get("inventory", {}).values() for units in sizes.values())


def list_stores() -> List[Dict[str, Any]]:
    return list(_load("stores.json", "stores"))


def get_customer(customer_id: str) -> Optional[Dict[str, Any]]:
    for customer in _load("customers.json", "customers"):
        if customer["customer_id"] == customer_id:
            return customer
    return None
