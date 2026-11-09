"""Loyalty discount, delivery options and order creation."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ai_workflow.schemas import Order
from ai_workflow.storage import catalog_store, postgres_store, redis_store
from ai_workflow.tools.cart import cart_total
from ai_workflow.tools.catalog import nearby_stores

BUNDLE_ITEMS = 3
BUNDLE_DISCOUNT = 0.20
MULTI_BUY_ITEMS = 2
MULTI_BUY_DISCOUNT = 0.10
MAX_POINTS_SHARE = 0.10
FREE_DELIVERY_FROM = 4000


def _next_offer(line_count: int) -> Optional[Dict[str, int]]:
    """What the next item would earn, or None when the best offer is already reached."""
    if line_count >= BUNDLE_ITEMS:
        return None
    if line_count >= MULTI_BUY_ITEMS:
        return {"items_needed": BUNDLE_ITEMS - line_count, "discount_percent": int(BUNDLE_DISCOUNT * 100)}
    return {"items_needed": MULTI_BUY_ITEMS - line_count, "discount_percent": int(MULTI_BUY_DISCOUNT * 100)}


def loyalty_discount(customer_id: str, cart: List[Dict[str, Any]], use_points: bool = False) -> Dict[str, Any]:
    """Multi-item discount, plus loyalty points only when the customer chose to use them.

    1 point is worth Rs 1, and at most 10% of the cart can be paid with points.
    `points_usable` is what they could use; `points_used` is what is taken off.
    """
    customer = catalog_store.get_customer(customer_id) or {}
    points_available = customer.get("loyalty_points", 0)
    cart_value = cart_total(cart)["total"]

    offers = []
    discount_amount = 0
    if len(cart) >= BUNDLE_ITEMS:
        offers.append("Bundle Offer: 20% off on 3+ items")
        discount_amount = cart_value * BUNDLE_DISCOUNT
    elif len(cart) >= MULTI_BUY_ITEMS:
        offers.append("Multi-buy: 10% off on 2+ items")
        discount_amount = cart_value * MULTI_BUY_DISCOUNT

    points_usable = min(points_available, cart_value * MAX_POINTS_SHARE)
    points_used = points_usable if use_points else 0
    final_price = cart_value - discount_amount - points_used
    return {
        "next_offer": _next_offer(len(cart)),
        "points_available": points_available,
        "points_value": points_available,
        "points_usable": points_usable,
        "points_used": points_used,
        "use_points": use_points,
        "offers": offers,
        "discount_amount": discount_amount,
        "original_price": cart_value,
        "final_price": final_price,
        "savings": cart_value - final_price,
    }


def delivery_options(cart: List[Dict[str, Any]], location: str) -> Dict[str, Any]:
    if not cart:
        return {"status": "no_order", "message": "No items to deliver"}

    pickup_store = nearby_stores(location)[0]["name"]
    options = [
        {"type": "express", "timeline": "Tomorrow 10 AM", "cost": 99, "available": True},
        {"type": "standard", "timeline": "2-3 days", "cost": 0, "available": True},
        {"type": "store_pickup", "timeline": "Today 6 PM", "cost": 0, "available": True, "store": pickup_store},
    ]
    free_delivery = cart_total(cart)["total"] > FREE_DELIVERY_FROM
    return {
        "status": "available",
        "delivery_options": options,
        "recommended": "standard" if free_delivery else "express",
        "timeline": "2-3 days" if free_delivery else "Tomorrow",
        "message": "Free delivery available!" if free_delivery else "Express delivery available",
    }


async def create_order(session: Dict[str, Any], payment_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build the order from the session cart and a successful payment, and save it."""
    order = Order(
        id=f"ORD{uuid.uuid4().hex[:8].upper()}",
        session_id=session["session_id"],
        customer_id=session["customer_id"],
        items=session["cart"],
        total=payment_result["amount"],
        payment_method=payment_result.get("method", "upi"),
        gateway=payment_result.get("gateway"),
        transaction_id=payment_result.get("transaction_id"),
        store=payment_result.get("store") or session.get("reserved_store"),
    ).model_dump(mode="json")
    await postgres_store.save_order(order)
    tell_store_about_pickup(order)
    return order


def tell_store_about_pickup(order: Dict[str, Any]) -> None:
    """When the customer reserved at a store, tell its associate the order is paid and will be collected."""
    if not order.get("store"):
        return
    alert = {
        "kind": "pickup",
        "store": order["store"],
        "items": [item["name"] for item in cart_total(order["items"])["items"]],
        "total": order["total"],
        "order_id": order["id"],
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }
    redis_store.update_session(order["session_id"], lambda session: session.update(store_alert=alert))
