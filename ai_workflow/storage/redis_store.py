"""Live sessions and carts in Redis."""

import json
import secrets
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import redis
from loguru import logger

from ai_workflow.settings import settings

_client: Optional[redis.Redis] = None

RATE_LIMIT_WINDOW_SECONDS = 60
IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60


def _redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.REDIS_URL.get_secret_value(), decode_responses=True)
    return _client


def ping_redis() -> None:
    _redis().ping()


def close_redis() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def create_session(customer_id: str = "CUST001", carry_over: bool = True) -> str:
    """Start a session. By default the cart, likes and history carry over from the customer's
    latest session; carry_over=False starts completely empty."""
    session_id = f"SESSION_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()
    session = {
        "session_id": session_id,
        "token": secrets.token_urlsafe(24),
        "customer_id": customer_id,
        "created_at": now,
        "last_activity": now,
        "channel": "web",
        "liked_products": [],
        "cart": [],
        "conversation_history": [],
        "location": "Mumbai",
        "reserved_store": None,
        "store_alert": None,
        "use_points": False,
        "last_payment": None,
        "status": "active",
    }
    latest_id = _redis().get(f"customer:{customer_id}:session")
    previous = get_session(latest_id) if (latest_id and carry_over) else None
    if previous:
        for field in ("liked_products", "cart", "conversation_history", "reserved_store"):
            session[field] = previous[field]
    save_session(session_id, session)
    _redis().set(f"customer:{customer_id}:session", session_id)
    logger.info("Created session {}", session_id)
    return session_id


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    raw = _redis().get(f"session:{session_id}")
    return json.loads(raw) if raw else None


def save_session(session_id: str, data: Dict[str, Any]) -> None:
    data["last_activity"] = datetime.now().isoformat()
    _redis().set(f"session:{session_id}", json.dumps(data), ex=settings.SESSION_TIMEOUT_SECONDS)


def update_session(session_id: str, change: Callable[[Dict[str, Any]], Any]) -> Any:
    """Change a session safely when several requests arrive at once.

    `change` edits the session in place and may return a value. If another request saved the
    session in the meantime, Redis rejects the write and the change is applied again to the
    fresh copy. Returns what `change` returned, or None when the session does not exist.
    """
    key = f"session:{session_id}"
    with _redis().pipeline() as pipe:
        while True:
            try:
                pipe.watch(key)
                raw = pipe.get(key)
                if not raw:
                    return None
                session = json.loads(raw)
                result = change(session)
                session["last_activity"] = datetime.now().isoformat()
                pipe.multi()
                pipe.set(key, json.dumps(session), ex=settings.SESSION_TIMEOUT_SECONDS)
                pipe.execute()
                return result
            except redis.WatchError:
                continue


def add_to_cart(session_id: str, product_id: str, quantity: int = 1, size: str = "40") -> Optional[List[Dict[str, Any]]]:
    def change(session):
        session["cart"].append({"product_id": product_id, "quantity": quantity, "size": size})
        return session["cart"]
    return update_session(session_id, change)


def update_cart_quantity(session_id: str, product_id: str, quantity: int) -> Optional[List[Dict[str, Any]]]:
    def change(session):
        for item in session["cart"]:
            if item["product_id"] == product_id:
                item["quantity"] = quantity
                break
        return session["cart"]
    return update_session(session_id, change)


def remove_from_cart(session_id: str, product_id: str) -> Optional[List[Dict[str, Any]]]:
    def change(session):
        session["cart"] = [item for item in session["cart"] if item["product_id"] != product_id]
        return session["cart"]
    return update_session(session_id, change)


def add_liked_product(session_id: str, product_id: str) -> Optional[List[str]]:
    def change(session):
        if product_id not in session["liked_products"]:
            session["liked_products"].append(product_id)
        return session["liked_products"]
    return update_session(session_id, change)


def is_rate_limited(identifier: str, limit: int) -> bool:
    """Count one request for this client. True once the client passes `limit` in the current minute."""
    key = f"ratelimit:{identifier}:{int(time.time() // RATE_LIMIT_WINDOW_SECONDS)}"
    count = _redis().incr(key)
    if count == 1:
        _redis().expire(key, RATE_LIMIT_WINDOW_SECONDS)
    return count > limit


def get_saved_response(session_id: str, idempotency_key: str) -> Optional[Dict[str, Any]]:
    raw = _redis().get(f"idempotency:{session_id}:{idempotency_key}")
    return json.loads(raw) if raw else None


def save_response(session_id: str, idempotency_key: str, response: Dict[str, Any]) -> None:
    _redis().set(f"idempotency:{session_id}:{idempotency_key}", json.dumps(response), ex=IDEMPOTENCY_TTL_SECONDS)
