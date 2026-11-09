"""Request bodies and shared data shapes."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CustomerRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=1000)
    channel: str = "web"  # mobile, whatsapp, web, store


class ProductLike(BaseModel):
    session_id: str
    product_id: str
    channel: str = "mobile"


class CartUpdate(BaseModel):
    session_id: str
    product_id: str
    quantity: int = Field(default=1, ge=1, le=99)
    size: Optional[str] = Field(default="40", max_length=10)
    # The pages still send these. The catalog is the source of truth, so they are ignored.
    product_name: Optional[str] = None
    price: Optional[float] = None


class CartRemove(BaseModel):
    session_id: str
    product_id: str


class StoreCheck(BaseModel):
    session_id: str
    product_id: str
    location: Optional[str] = "Mumbai"


class PaymentRequest(BaseModel):
    session_id: str
    amount: Optional[float] = None  # ignored: the server prices the cart
    method: str = "upi"


class OrderComplete(BaseModel):
    session_id: str
    items: List[Dict[str, Any]] = []
    payment_method: str = "upi"
    total: Optional[float] = None
    store: Optional[str] = None
    kiosk: Optional[str] = None


class FeedbackRating(BaseModel):
    session_id: str
    rating: int = Field(ge=1, le=5)
    order_id: Optional[str] = None


class ApprovalDecision(BaseModel):
    session_id: str
    approved: bool


class CartItem(BaseModel):
    product_id: str
    quantity: int = 1
    size: Optional[str] = Field(default="40", max_length=10)


class Order(BaseModel):
    id: str
    session_id: str
    customer_id: str
    items: List[Dict[str, Any]]
    total: float
    payment_method: str
    gateway: Optional[str] = None
    transaction_id: Optional[str] = None
    store: Optional[str] = None
    status: str = "confirmed"
    created_at: Optional[datetime] = None
