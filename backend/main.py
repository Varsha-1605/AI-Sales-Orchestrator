"""
Main FastAPI Application
AI Sales Orchestrator for Omnichannel Retail
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import json
from typing import Dict, List
import asyncio

from config import settings
from graph.orchestrator_graph import create_orchestrator_graph
from memory.session_manager import SessionManager
from models.schemas import (
    CustomerRequest,
    ProductLike,
    CartUpdate,
    StoreCheck,
    PaymentRequest
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_agent_update(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                print(f"Error sending message: {e}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting AI Sales Orchestrator...")
    app.state.session_manager = SessionManager()
    app.state.orchestrator = create_orchestrator_graph()
    print("✅ System ready!")
    yield
    # Shutdown
    print("👋 Shutting down...")

# Create FastAPI app
app = FastAPI(
    title="AI Sales Orchestrator",
    description="Multi-agent system for omnichannel retail",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# HTTP ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {
        "message": "AI Sales Orchestrator API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

@app.post("/api/session/create")
async def create_session(customer_id: str = "CUST001"):
    """Create a new shopping session"""
    session_id = app.state.session_manager.create_session(customer_id)
    return {
        "session_id": session_id,
        "customer_id": customer_id,
        "message": "Session created successfully"
    }

@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session details"""
    session = app.state.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

# ============================================================================
# PRODUCT INTERACTIONS
# ============================================================================

@app.post("/api/products/like")
async def like_product(like: ProductLike):
    """Customer likes a product"""
    session = app.state.session_manager.get_session(like.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Add to liked products
    if like.product_id not in session["liked_products"]:
        session["liked_products"].append(like.product_id)
        app.state.session_manager.save_session(like.session_id, session)
    
    # Broadcast update
    await manager.send_agent_update(like.session_id, {
        "type": "product_liked",
        "product_id": like.product_id,
        "total_likes": len(session["liked_products"])
    })
    
    return {
        "success": True,
        "liked_products": session["liked_products"]
    }

@app.get("/api/products/recommendations/{session_id}")
async def get_recommendations(session_id: str):
    """Get AI-powered product recommendations"""
    session = app.state.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Broadcast agent activity
    await manager.send_agent_update(session_id, {
        "type": "agent_called",
        "agent": "recommendation",
        "status": "processing"
    })
    
    # Call orchestrator
    request = CustomerRequest(
        session_id=session_id,
        message="Show me recommendations based on my likes",
        channel="web"
    )
    
    result = await run_orchestrator(request)
    
    return result

# ============================================================================
# CART MANAGEMENT
# ============================================================================

@app.post("/api/cart/add")
async def add_to_cart(cart_update: CartUpdate):
    """Add item to cart"""
    session = app.state.session_manager.get_session(cart_update.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Add to cart
    session["cart"].append({
        "product_id": cart_update.product_id,
        "quantity": cart_update.quantity,
        "size": cart_update.size
    })
    app.state.session_manager.save_session(cart_update.session_id, session)
    
    # Broadcast update
    await manager.send_agent_update(cart_update.session_id, {
        "type": "cart_updated",
        "cart": session["cart"]
    })
    
    return {
        "success": True,
        "cart": session["cart"]
    }

@app.post("/api/cart/update")
async def update_cart(cart_update: CartUpdate):
    """Update cart quantity - triggers edge case demo"""
    session = app.state.session_manager.get_session(cart_update.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Simulate agent orchestration for recalculation
    await manager.send_agent_update(cart_update.session_id, {
        "type": "agent_called",
        "agent": "inventory",
        "status": "checking_stock",
        "message": "Checking availability for updated quantity..."
    })
    
    await asyncio.sleep(0.3)
    
    await manager.send_agent_update(cart_update.session_id, {
        "type": "agent_called",
        "agent": "loyalty",
        "status": "calculating",
        "message": "Recalculating discounts..."
    })
    
    await asyncio.sleep(0.3)
    
    # Update cart
    for item in session["cart"]:
        if item["product_id"] == cart_update.product_id:
            item["quantity"] = cart_update.quantity
            break
    
    app.state.session_manager.save_session(cart_update.session_id, session)
    
    return {
        "success": True,
        "cart": session["cart"],
        "new_discount": "10% off applied!",
        "message": "Updated quantity to 2. New total: ₹4,350"
    }

# ============================================================================
# STORE OPERATIONS
# ============================================================================

@app.post("/api/store/check")
async def check_store_availability(store_check: StoreCheck):
    """Check product availability in nearby stores"""
    session = app.state.session_manager.get_session(store_check.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Call inventory agent
    await manager.send_agent_update(store_check.session_id, {
        "type": "agent_called",
        "agent": "inventory",
        "status": "searching",
        "message": "Checking 5 nearest stores..."
    })
    
    await asyncio.sleep(0.5)
    
    # Mock response
    stores = [
        {"name": "Bandra Store", "distance": "2km", "stock": 3},
        {"name": "Powai Store", "distance": "5km", "stock": 1},
        {"name": "Andheri Store", "distance": "7km", "stock": 0}
    ]
    
    return {
        "success": True,
        "stores": stores,
        "recommended": "Bandra Store"
    }

@app.post("/api/store/reserve")
async def reserve_items(session_id: str, store_name: str):
    """Reserve items at store"""
    session = app.state.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session["reserved_store"] = store_name
    app.state.session_manager.save_session(session_id, session)
    
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

@app.post("/api/payment/process")
async def process_payment(payment: PaymentRequest):
    """Process payment with auto-retry on failure (Edge Case #1)"""
    session = app.state.session_manager.get_session(payment.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Simulate payment agent trying multiple gateways
    await manager.send_agent_update(payment.session_id, {
        "type": "agent_called",
        "agent": "payment",
        "status": "processing",
        "message": "Processing payment via Gateway 1..."
    })
    
    await asyncio.sleep(1)
    
    # Gateway 1 fails
    await manager.send_agent_update(payment.session_id, {
        "type": "payment_status",
        "gateway": "Gateway 1",
        "status": "failed",
        "reason": "Timeout error",
        "message": "Gateway 1 failed. Trying alternate..."
    })
    
    await asyncio.sleep(0.8)
    
    # Gateway 2 fails
    await manager.send_agent_update(payment.session_id, {
        "type": "payment_status",
        "gateway": "Gateway 2",
        "status": "failed",
        "reason": "Bank declined",
        "message": "Gateway 2 failed. Switching to UPI..."
    })
    
    await asyncio.sleep(0.7)
    
    # UPI succeeds
    await manager.send_agent_update(payment.session_id, {
        "type": "payment_status",
        "gateway": "UPI Direct",
        "status": "success",
        "transaction_id": "TXN123456789",
        "message": "Payment successful via UPI!"
    })
    
    return {
        "success": True,
        "message": "Payment declined. Trying alternate gateway... Success with UPI!",
        "transaction_id": "TXN123456789",
        "total_time": "2.7s"
    }

# ============================================================================
# CONVERSATIONAL AI (Main Orchestrator)
# ============================================================================

@app.post("/api/chat")
async def chat(request: CustomerRequest):
    """Main conversational endpoint - routes to orchestrator"""
    session = app.state.session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Run orchestrator
    result = await run_orchestrator(request)
    
    return result

async def run_orchestrator(request: CustomerRequest):
    """Execute the LangGraph orchestrator"""
    try:
        # Get session
        session = app.state.session_manager.get_session(request.session_id)
        
        # Broadcast orchestrator start
        await manager.send_agent_update(request.session_id, {
            "type": "orchestrator_start",
            "message": "Analyzing request...",
            "request": request.message
        })
        
        # Run graph
        graph = app.state.orchestrator
        result = await graph.ainvoke({
            "session_id": request.session_id,
            "customer_id": session["customer_id"],
            "channel": request.channel,
            "current_request": request.message,
            "messages": session.get("conversation_history", []),
            "liked_products": session.get("liked_products", []),
            "cart": session.get("cart", []),
            "location": session.get("location", "Mumbai"),
            "agent_calls": [],
            "response": ""
        })
        
        # Update session with conversation
        session["conversation_history"].append({
            "role": "user",
            "content": request.message,
            "channel": request.channel
        })
        session["conversation_history"].append({
            "role": "assistant",
            "content": result["response"],
            "channel": request.channel
        })
        app.state.session_manager.save_session(request.session_id, session)
        
        # Broadcast completion
        await manager.send_agent_update(request.session_id, {
            "type": "orchestrator_complete",
            "response": result["response"],
            "agents_used": result.get("agent_calls", [])
        })
        
        return result
        
    except Exception as e:
        print(f"Error in orchestrator: {e}")
        return {
            "success": False,
            "response": "I apologize, but I'm having trouble processing your request. Please try again.",
            "error": str(e)
        }

# ============================================================================
# WEBSOCKET FOR REAL-TIME UPDATES
# ============================================================================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket connection for real-time agent updates"""
    await manager.connect(websocket, session_id)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to AI Orchestrator",
            "session_id": session_id
        })
        
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back for testing
            await websocket.send_json({
                "type": "echo",
                "data": data
            })
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        print(f"Client {session_id} disconnected")

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.FASTAPI_HOST,
        port=settings.FASTAPI_PORT,
        reload=settings.DEBUG_MODE
    )