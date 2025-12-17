"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# ============================================================================
# REQUEST MODELS
# ============================================================================

class CustomerRequest(BaseModel):
    session_id: str
    message: str
    channel: str = "web"  # mobile, whatsapp, web, store
    
class ProductLike(BaseModel):
    session_id: str
    product_id: str
    channel: str = "mobile"

class CartUpdate(BaseModel):
    session_id: str
    product_id: str
    quantity: int = 1
    size: Optional[str] = "40"

class StoreCheck(BaseModel):
    session_id: str
    product_id: str
    location: Optional[str] = "Mumbai"

class PaymentRequest(BaseModel):
    session_id: str
    amount: float
    method: str = "upi"

# ============================================================================
# SESSION MODELS
# ============================================================================

class CustomerProfile(BaseModel):
    customer_id: str
    name: str
    phone: str
    location: str
    loyalty_points: int = 0
    preferences: Dict[str, Any] = {}

class ShoppingSession(BaseModel):
    session_id: str
    customer_id: str
    channel: str
    created_at: datetime
    liked_products: List[str] = []
    cart: List[Dict[str, Any]] = []
    conversation_history: List[Dict[str, Any]] = []
    location: str = "Mumbai"
    reserved_store: Optional[str] = None

# ============================================================================
# AGENT RESPONSE MODELS
# ============================================================================

class AgentResponse(BaseModel):
    agent_name: str
    status: str  # success, failed, processing
    data: Dict[str, Any]
    execution_time: float
    reasoning: Optional[str] = None

class OrchestratorResponse(BaseModel):
    success: bool
    response: str
    agents_called: List[str]
    agent_responses: List[AgentResponse] = []
    next_action: Optional[str] = None

# ============================================================================
# PRODUCT MODELS
# ============================================================================

class Product(BaseModel):
    product_id: str
    name: str
    brand: str
    price: float
    sizes: List[str]
    colors: List[str]
    category: str
    tags: List[str]
    image: str
    inventory: Dict[str, Dict[str, int]]  # store -> size -> quantity

class ProductRecommendation(BaseModel):
    product_id: str
    confidence: float
    reasoning: str

# ============================================================================
# EDGE CASE MODELS
# ============================================================================

class PaymentRetryStatus(BaseModel):
    gateway: str
    status: str  # success, failed, processing
    reason: Optional[str] = None
    timestamp: datetime

class StockAlternative(BaseModel):
    store_name: str
    distance: str
    stock_available: int
    alternative_products: List[str] = []