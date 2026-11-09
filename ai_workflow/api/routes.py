"""REST routes used by the frontend pages."""

import secrets
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from ai_workflow.channels.base import IncomingMessage, handle_message, resume_after_approval
from ai_workflow.channels.stream import stream_reply
from ai_workflow.channels.websocket_manager import manager
from ai_workflow.integrations.payments.base import GatewayResult
from ai_workflow.integrations.payments.charge import charge
from ai_workflow.integrations.translation import translate
from ai_workflow.schemas import (
    ApprovalDecision,
    CartRemove,
    CartUpdate,
    CustomerRequest,
    FeedbackRating,
    OrderComplete,
    PaymentRequest,
    ProductLike,
    StoreCheck,
)
from ai_workflow.settings import settings
from ai_workflow.storage import catalog_store, postgres_store, redis_store
from ai_workflow.tools.cart import cart_total
from ai_workflow.tools.catalog import check_stock
from ai_workflow.tools.orders import create_order, loyalty_discount

DEFAULT_SIZE = "40"
TOKEN_HEADER = "X-Session-Token"
# Tell browsers and proxies (Nginx) not to hold back streamed text
STREAM_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def rate_limit(request: Request) -> None:
    """Stop one client from sending too many requests in a minute."""
    client = request.client.host if request.client else "unknown"
    if redis_store.is_rate_limited(client, settings.RATE_LIMIT_PER_MINUTE):
        raise HTTPException(status_code=429, detail="Too many requests, please slow down")


router = APIRouter()
limited = [Depends(rate_limit)]


def _session_or_404(session_id: str, request: Request) -> Dict[str, Any]:
    """Load the session. When AUTH_ENABLED, the request must carry the session's token."""
    session = redis_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if settings.AUTH_ENABLED:
        sent_token = request.headers.get(TOKEN_HEADER, "")
        if not session.get("token") or not secrets.compare_digest(sent_token, session["token"]):
            raise HTTPException(status_code=401, detail="Invalid or missing session token")
    return session


def _known_product_or_404(product_id: str) -> None:
    if not catalog_store.get_product(product_id):
        raise HTTPException(status_code=404, detail="Unknown product")


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

@router.post("/api/session/create", dependencies=limited)
async def create_session(customer_id: str = "CUST001", fresh: bool = False):
    """Create a new shopping session. The returned token must be sent back as X-Session-Token.

    fresh=true starts with an empty cart and no likes instead of continuing the customer's last session."""
    if not catalog_store.get_customer(customer_id):
        raise HTTPException(status_code=404, detail="Unknown customer")
    session_id = redis_store.create_session(customer_id, carry_over=not fresh)
    return {
        "session_id": session_id,
        "customer_id": customer_id,
        "token": redis_store.get_session(session_id)["token"],
        "message": "Session created successfully"
    }

@router.get("/api/session/{session_id}")
async def get_session(session_id: str, request: Request):
    """Get session details (without the secret token)"""
    session = _session_or_404(session_id, request)
    return {key: value for key, value in session.items() if key != "token"}

# ============================================================================
# PRODUCT INTERACTIONS
# ============================================================================

@router.post("/api/products/like")
async def like_product(like: ProductLike, request: Request):
    """Customer likes a product"""
    _session_or_404(like.session_id, request)
    _known_product_or_404(like.product_id)
    liked_products = redis_store.add_liked_product(like.session_id, like.product_id)

    await manager.send_agent_update(like.session_id, {
        "type": "product_liked",
        "product_id": like.product_id,
        "total_likes": len(liked_products)
    })

    return {
        "success": True,
        "liked_products": liked_products
    }

@router.get("/api/products/recommendations/{session_id}", dependencies=limited)
async def get_recommendations(session_id: str, request: Request):
    """Get AI-powered product recommendations"""
    _session_or_404(session_id, request)

    await manager.send_agent_update(session_id, {
        "type": "agent_called",
        "agent": "recommendation",
        "status": "processing"
    })

    message = IncomingMessage(session_id, "Show me recommendations based on my likes", "web")
    return await handle_message(message, request.app.state.graph, manager)

# ============================================================================
# CART MANAGEMENT
# ============================================================================

@router.get("/api/cart/{session_id}")
async def get_cart(session_id: str, request: Request):
    """The shared cart with names, prices and the total (all pages read this)"""
    session = _session_or_404(session_id, request)
    return {
        "success": True,
        **cart_total(session["cart"]),
        "pricing": loyalty_discount(session["customer_id"], session["cart"], session.get("use_points", False)),
    }

@router.post("/api/cart/points")
async def choose_to_use_points(session_id: str, use: bool, request: Request):
    """The customer chooses whether loyalty points are used on this cart. Returns the new price."""
    _session_or_404(session_id, request)

    def choose(session):
        session["use_points"] = use
        return session
    session = redis_store.update_session(session_id, choose)
    return {"success": True, "pricing": loyalty_discount(session["customer_id"], session["cart"], use)}

@router.get("/api/products/availability")
async def product_availability():
    """Which products can be bought at all, so pages can show Available or Out of stock."""
    return {"availability": {p["product_id"]: catalog_store.is_in_stock(p["product_id"]) for p in catalog_store.list_products()}}

@router.post("/api/cart/add")
async def add_to_cart(cart_update: CartUpdate, request: Request):
    """Add item to cart"""
    session = _session_or_404(cart_update.session_id, request)
    _known_product_or_404(cart_update.product_id)
    stock = check_stock(cart_update.product_id, cart_update.size, session["location"])
    if not stock["available"]:
        raise HTTPException(status_code=409, detail={
            "message": "This item is out of stock in every nearby store.",
            "alternatives": stock["alternatives"],
        })
    cart = redis_store.add_to_cart(
        cart_update.session_id, cart_update.product_id, cart_update.quantity, cart_update.size
    )

    await manager.send_agent_update(cart_update.session_id, {
        "type": "cart_updated",
        "cart": cart
    })

    return {
        "success": True,
        "cart": cart
    }

@router.post("/api/cart/update")
async def update_cart(cart_update: CartUpdate, request: Request):
    """Update cart quantity and recalculate the total and discount"""
    session = _session_or_404(cart_update.session_id, request)

    await manager.send_agent_update(cart_update.session_id, {
        "type": "agent_called",
        "agent": "inventory",
        "status": "checking_stock",
        "message": "Checking availability for updated quantity..."
    })

    await manager.send_agent_update(cart_update.session_id, {
        "type": "agent_called",
        "agent": "loyalty",
        "status": "calculating",
        "message": "Recalculating discounts..."
    })

    cart = redis_store.update_cart_quantity(cart_update.session_id, cart_update.product_id, cart_update.quantity)
    discount = loyalty_discount(session["customer_id"], cart, session.get("use_points", False))

    return {
        "success": True,
        "cart": cart,
        "new_discount": discount["offers"][0] if discount["offers"] else "No discount applied",
        "message": f"Updated quantity to {cart_update.quantity}. New total: ₹{discount['final_price']:,.0f}"
    }

@router.post("/api/cart/remove")
async def remove_from_cart(cart_remove: CartRemove, request: Request):
    """Remove item from cart"""
    _session_or_404(cart_remove.session_id, request)
    cart = redis_store.remove_from_cart(cart_remove.session_id, cart_remove.product_id)

    return {
        "success": True,
        "cart": cart,
        "message": "Item removed from cart"
    }

# ============================================================================
# STORE OPERATIONS
# ============================================================================

@router.post("/api/store/check")
async def check_store_availability(store_check: StoreCheck, request: Request):
    """Check product availability in nearby stores"""
    session = _session_or_404(store_check.session_id, request)
    _known_product_or_404(store_check.product_id)
    size = next(
        (item.get("size", DEFAULT_SIZE) for item in session["cart"] if item["product_id"] == store_check.product_id),
        DEFAULT_SIZE,
    )
    stock = check_stock(store_check.product_id, size, store_check.location)

    await manager.send_agent_update(store_check.session_id, {
        "type": "agent_called",
        "agent": "inventory",
        "status": "searching",
        "message": f"Checking {len(stock['stores'])} nearest stores..."
    })

    return {
        "success": True,
        "stores": stock["stores"],
        "recommended": stock.get("store")
    }

@router.post("/api/store/alert/respond")
async def respond_to_store_alert(session_id: str, action: str, request: Request):
    """The associate accepts or rejects the reservation or pickup the customer is waiting on."""
    _session_or_404(session_id, request)
    if action not in ("accept", "reject"):
        raise HTTPException(status_code=400, detail="action must be accept or reject")

    def respond(session):
        alert = session.get("store_alert")
        if not alert:
            return None
        alert["status"] = "accepted" if action == "accept" else "rejected"
        if action == "reject" and alert["kind"] == "reservation":
            session["reserved_store"] = None
        return alert
    alert = redis_store.update_session(session_id, respond)
    if not alert:
        raise HTTPException(status_code=404, detail="Nothing is waiting for the store")

    await manager.send_agent_update(session_id, {
        "type": "store_alert_response",
        "store": alert["store"],
        "kind": alert["kind"],
        "status": alert["status"],
    })
    return {"success": True, "status": alert["status"]}

@router.post("/api/store/reserve")
async def reserve_items(session_id: str, store_name: str, request: Request):
    """Reserve items at store"""
    session = _session_or_404(session_id, request)
    if store_name not in {store["name"] for store in catalog_store.list_stores()}:
        raise HTTPException(status_code=404, detail="Unknown store")

    alert = {
        "kind": "reservation",
        "store": store_name,
        "items": [item["name"] for item in cart_total(session["cart"])["items"]],
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }

    def reserve(session):
        session["reserved_store"] = store_name
        session["store_alert"] = alert
    redis_store.update_session(session_id, reserve)

    await manager.send_agent_update(session_id, {
        "type": "items_reserved",
        "store": store_name,
        "message": f"Items reserved at {store_name} for 24 hours"
    })

    return {
        "success": True,
        "message": f"Reserved at {store_name} for 24 hours!",
        "store": store_name
    }

# ============================================================================
# PAYMENT PROCESSING (with Edge Case Demo)
# ============================================================================

@router.post("/api/payment/process", dependencies=limited)
async def process_payment(
    payment_request: PaymentRequest,
    request: Request,
    idempotency_key: Optional[str] = Header(default=None),
):
    """Charge the cart total with automatic failover across gateways (Edge Case #1).

    The amount is worked out from the server-side cart; any amount sent by the page is ignored.
    Send an Idempotency-Key header to make a retried request return the first result instead of charging again.
    """
    session_id = payment_request.session_id
    session = _session_or_404(session_id, request)
    if idempotency_key:
        saved = redis_store.get_saved_response(session_id, idempotency_key)
        if saved:
            return saved
    if not session["cart"]:
        raise HTTPException(status_code=400, detail="Cart is empty")
    amount = loyalty_discount(session["customer_id"], session["cart"], session.get("use_points", False))["final_price"]

    async def send_attempt(gateway: str, result: GatewayResult):
        await manager.send_agent_update(session_id, {
            "type": "payment_status",
            "gateway": gateway,
            "status": "success" if result.success else "failed",
            "reason": result.reason,
            "message": f"Payment successful via {gateway}!" if result.success else f"{gateway} failed. Trying alternate...",
            "transaction_id": result.transaction_id
        })

    await manager.send_agent_update(session_id, {
        "type": "agent_called",
        "agent": "payment",
        "status": "processing",
        "message": "Processing payment..."
    })

    payment = await charge(amount, on_attempt=send_attempt)
    if payment["success"]:
        paid = {key: payment[key] for key in ("amount", "gateway", "transaction_id")}
        paid["method"] = payment_request.method

        def remember_payment(session):
            session["last_payment"] = paid
        redis_store.update_session(session_id, remember_payment)

    response = {
        "success": payment["success"],
        "message": payment["message"],
        "amount": payment.get("amount"),
        "transaction_id": payment.get("transaction_id"),
        "total_time": payment["total_time"]
    }
    if idempotency_key:
        redis_store.save_response(session_id, idempotency_key, response)
    return response

@router.post("/api/order/complete", dependencies=limited)
async def complete_order(order: OrderComplete, request: Request):
    """Save the order for the payment just made (the kiosk calls this after paying).

    Needs a successful /api/payment/process first. Items and total come from the server,
    and the payment is used once, so repeating the call cannot create a second order.
    """
    session_id = order.session_id
    _session_or_404(session_id, request)

    def take_payment(session):
        if not session.get("last_payment"):
            return None
        taken = {"payment": session["last_payment"], "cart": session["cart"]}
        session["last_payment"] = None
        session["cart"] = []
        session["use_points"] = False
        return taken

    taken = redis_store.update_session(session_id, take_payment)
    if not taken:
        raise HTTPException(status_code=402, detail="Payment required before completing an order")

    paid = {**taken["payment"], "method": order.payment_method, "store": order.store}
    session = redis_store.get_session(session_id)
    saved = await create_order({**session, "cart": taken["cart"]}, paid)
    return {"success": True, "order_id": saved["id"]}

@router.post("/api/feedback/rating")
async def save_rating(feedback: FeedbackRating, request: Request):
    """Save a post-purchase rating"""
    _session_or_404(feedback.session_id, request)
    await postgres_store.save_feedback(feedback.session_id, feedback.order_id, feedback.rating)
    return {"success": True}

# ============================================================================
# CONVERSATIONAL AI (Main Orchestrator)
# ============================================================================

@router.post("/api/chat", dependencies=limited)
async def chat(chat_request: CustomerRequest, request: Request):
    """Main conversational endpoint - routes to orchestrator"""
    _session_or_404(chat_request.session_id, request)
    message = IncomingMessage(chat_request.session_id, chat_request.message, chat_request.channel)
    return await handle_message(message, request.app.state.graph, manager)

@router.post("/api/chat/stream", dependencies=limited)
async def chat_stream(chat_request: CustomerRequest, request: Request):
    """Same as /api/chat, but the reply arrives piece by piece (server-sent events)."""
    _session_or_404(chat_request.session_id, request)
    message = IncomingMessage(chat_request.session_id, chat_request.message, chat_request.channel)
    graph = request.app.state.graph
    return StreamingResponse(
        stream_reply(manager, lambda sender: handle_message(message, graph, sender)),
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
    )

@router.post("/api/chat/approve/stream", dependencies=limited)
async def approve_stream(decision: ApprovalDecision, request: Request):
    """Same as /api/chat/approve, but streamed."""
    _session_or_404(decision.session_id, request)
    graph = request.app.state.graph
    return StreamingResponse(
        stream_reply(
            manager,
            lambda sender: resume_after_approval(decision.session_id, decision.approved, graph, sender),
        ),
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
    )

@router.post("/api/chat/approve", dependencies=limited)
async def approve(decision: ApprovalDecision, request: Request):
    """Customer's answer to an approval question (for example before payment)"""
    _session_or_404(decision.session_id, request)
    return await resume_after_approval(decision.session_id, decision.approved, request.app.state.graph, manager)

# ============================================================================
# TRANSLATION ENDPOINT
# ============================================================================

@router.post("/api/translate", dependencies=limited)
async def translate_text(request: dict):
    """
    Translate text using Google Translate API
    Supports multilingual customer interactions
    """
    text = request.get("text", "")
    if not text or len(text) > 2000:
        raise HTTPException(status_code=400, detail="Text is required and must be under 2000 characters")

    return await translate(text, request.get("source_lang", "auto"), request.get("target_lang", "en"))
