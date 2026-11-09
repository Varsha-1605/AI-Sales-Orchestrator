"""Cart totals using catalog prices."""

from typing import Any, Dict, List

from ai_workflow.storage import catalog_store


def cart_total(cart: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Line items with catalog prices and the cart total. Items not in the catalog are skipped."""
    items = []
    for line in cart:
        product = catalog_store.get_product(line["product_id"])
        if not product:
            continue
        quantity = line.get("quantity", 1)
        items.append({
            "product_id": product["product_id"],
            "name": product["name"],
            "price": product["price"],
            "quantity": quantity,
            "size": line.get("size"),
            "line_total": product["price"] * quantity,
        })
    return {"items": items, "total": sum(item["line_total"] for item in items)}
