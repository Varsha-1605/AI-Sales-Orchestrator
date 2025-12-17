# 🤖 AI Sales Orchestrator for Omnichannel Retail

> Multi-agent system powered by LangChain + LangGraph for seamless shopping experiences across mobile, web, chat, and physical stores.

## 🎯 Overview

This prototype demonstrates an AI-powered sales orchestration system that:
- ✅ Unifies customer context across all channels (mobile → WhatsApp → store)
- ✅ Uses 6 specialized AI agents coordinated by LangGraph
- ✅ Handles edge cases automatically (payment retry, out of stock, order modifications)
- ✅ Provides real-time agent visualization
- ✅ Maintains persistent memory across sessions

## 🏗️ Architecture

```
┌─────────────────┐
│  Orchestrator   │ ← Master coordinator (LangGraph)
└────────┬────────┘
         ↓
    ┌────┴────┐
    │ Agents  │
    └─────────┘
    ├─ Recommendation Agent (Product suggestions)
    ├─ Inventory Agent (Stock management)
    ├─ Payment Agent (Transaction processing)
    ├─ Fulfillment Agent (Delivery scheduling)
    ├─ Loyalty Agent (Offers & points)
    └─ Support Agent (Returns & issues)
```

## 📦 Tech Stack

**Backend:**
- FastAPI (async web framework)
- LangChain (AI framework)
- LangGraph (multi-agent orchestration)
- Claude API (Anthropic)
- WebSockets (real-time updates)
- Persistent file-based storage

**Frontend:**
- HTML5, CSS3, JavaScript (Vanilla)
- WebSocket client
- Responsive design

## 🚀 Quick Start

### Prerequisites

```bash
# Required
- Python 3.9+
- pip
- Claude API key (from console.anthropic.com)

# Optional
- Git
```

### Installation

1. **Clone/Download the project**

```bash
git clone <your-repo>
cd retail-ai-orchestrator
```

2. **Install Python dependencies**

```bash
cd backend
pip install -r requirements.txt
```

3. **Set up environment variables**

Create `backend/.env` file:

```env
# Claude API
ANTHROPIC_API_KEY=sk-ant-xxxxx
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Server
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
DEBUG_MODE=True

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

4. **Create data files**

```bash
cd backend
mkdir -p data
touch data/products.json data/customers.json data/stores.json data/sessions.json
```

Copy the JSON data from the mock_data artifact into respective files.

5. **Start the backend server**

```bash
cd backend
python main.py

# Or with uvicorn directly:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
🚀 Starting AI Sales Orchestrator...
✅ System ready!
INFO:     Uvicorn running on http://0.0.0.0:8000
```

6. **Start the frontend server**

```bash
# In a new terminal
cd frontend
python -m http.server 3000
```

7. **Open the demo**

Visit: `http://localhost:3000/index.html`

## 📱 Demo Flow

### The Complete Journey

1. **Mobile App** (`mobile.html`)
   - Browse products
   - Like 3 items (try the blue shirt!)
   - Click "Continue on WhatsApp"

2. **WhatsApp Chat** (`whatsapp.html`)
   - AI remembers your likes
   - Add items to cart
   - Get recommendations
   - Check store availability

3. **Store Dashboard** (`store-dashboard.html`)
   - Store associate sees your online activity
   - Your cart contents
   - AI-powered recommendations
   - Apply bundle offers

4. **Checkout & Edge Cases** (`agent-monitor.html`)
   - Watch payment retry in action
   - See out-of-stock handling
   - Order modification demo

## 🎬 Edge Case Demonstrations

### 1. Payment Retry (Edge Case #1)

**Scenario:** Payment gateway fails → automatic retry

```
Gateway 1 (Razorpay) → FAILED (timeout)
    ↓
Gateway 2 (PayU) → FAILED (bank declined)
    ↓
UPI Direct → SUCCESS
    ↓
Total time: 2.7 seconds (automatic!)
```

**Demo:**
- Open Agent Monitor
- Click "💳 Payment Retry"
- Watch agents handle failures automatically

### 2. Out of Stock (Edge Case #2)

**Scenario:** Product unavailable → find alternatives

```
Check current store → OUT OF STOCK
    ↓
Scan 5 nearby stores → Found at 2 locations
    ↓
Find alternative products → 2 variants available
    ↓
Notify customer with 3 options
```

**Demo:**
- Open Agent Monitor
- Click "📦 Out of Stock"
- See inventory agent providing alternatives

### 3. Order Modification (Edge Case #3)

**Scenario:** Customer changes quantity → recalculate everything

```
Change quantity 1 → 2
    ↓
Parallel execution:
├─ Inventory: Check stock ✓
├─ Loyalty: Recalculate offers ✓
└─ Payment: Update total ✓
    ↓
New discount applied automatically
Total time: 1.6 seconds
```

**Demo:**
- Open Agent Monitor
- Click "✏️ Order Modify"
- Watch parallel agent coordination

## 🔧 API Endpoints

### Session Management

```http
POST /api/session/create?customer_id=CUST001
GET  /api/session/{session_id}
```

### Product Interactions

```http
POST /api/products/like
GET  /api/products/recommendations/{session_id}
```

### Cart Operations

```http
POST /api/cart/add
POST /api/cart/update
```

### Store Operations

```http
POST /api/store/check
POST /api/store/reserve
```

### Payment

```http
POST /api/payment/process
```

### AI Chat

```http
POST /api/chat
```

### WebSocket

```
WS /ws/{session_id}
```

## 📊 Agent Visualization

The Agent Monitor shows:
- Real-time agent status (idle/processing/success/failed)
- Execution logs with timestamps
- Agent call counts
- Total orchestration metrics

**Color Coding:**
- 🔵 Blue: Orchestrator
- 🟡 Yellow: Recommendation
- 🟣 Purple: Inventory
- 🟢 Green: Payment Success
- 🔴 Red: Errors

## 💾 Persistent Memory

### How It Works

```python
Session Data (stored in data/sessions.json):
{
  "session_id": "SESSION_abc123",
  "customer_id": "CUST001",
  "liked_products": ["VH001", "VH002"],
  "cart": [{...}],
  "conversation_history": [{...}],
  "channel": "whatsapp",
  "reserved_store": "Bandra Store"
}
```

### Cross-Channel Context

```
Mobile App    → Likes products → Saved to session
     ↓
WhatsApp Chat → Reads session  → Sees likes
     ↓
Store Visit   → Reads session  → Knows history
```

## 🎨 Customization

### Adding New Products

Edit `backend/data/products.json`:

```json
{
  "product_id": "VH009",
  "name": "Your Product Name",
  "price": 2999,
  "category": "Category",
  "tags": ["tag1", "tag2"]
}
```

### Adding New Agents

1. Create `backend/agents/your_agent.py`:

```python
from agents.base_agent import BaseAgent

class YourAgent(BaseAgent):
    def __init__(self):
        super().__init__("Your Agent", "Description")
    
    async def _execute(self, state):
        # Your logic here
        return {"result": "data"}
```

2. Register in `backend/graph/orchestrator_graph.py`

### Customizing UI

All frontend files are in `frontend/`:
- `index.html` - Main controller
- `mobile.html` - Mobile app view
- `whatsapp.html` - Chat interface
- `store-dashboard.html` - Store view
- `agent-monitor.html` - Agent visualization

CSS is inline for easy customization.

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check Python version
python --version  # Should be 3.9+

# Install dependencies again
pip install -r requirements.txt

# Check port availability
lsof -i :8000  # Kill any process using port 8000
```

### Frontend can't connect to backend

1. Check CORS settings in `backend/config.py`
2. Ensure backend is running on port 8000
3. Check browser console for errors

### Claude API errors

```bash
# Check API key
echo $ANTHROPIC_API_KEY

# Test API key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"
```

### Session not persisting

1. Check `backend/data/sessions.json` exists
2. Verify write permissions
3. Check browser localStorage for `session_id`

## 📈 Performance Metrics

**Expected Response Times:**
- Session creation: <100ms
- Product like: <50ms
- AI chat response: 1-3s
- Agent orchestration: 0.5-2s
- Payment with retry: 2-3s
- WebSocket updates: <50ms

**Agent Execution Times:**
- Orchestrator: 0.1-0.3s
- Recommendation: 0.3-0.8s
- Inventory: 0.2-0.5s
- Payment: 0.5-2.5s (with retries)
- Loyalty: 0.2-0.4s
- Support: 0.2-0.5s

## 🎯 Key Features for Judging

### 1. Multi-Agent Orchestration ⭐⭐⭐
- LangGraph-based workflow
- 6 specialized agents
- Parallel execution
- Smart routing

### 2. Persistent Memory ⭐⭐⭐
- Cross-channel context
- File-based storage
- Session management
- Conversation history

### 3. Real-time Visualization ⭐⭐
- WebSocket updates
- Agent status monitoring
- Live logs
- Performance metrics

### 4. Edge Case Handling ⭐⭐⭐
- Payment auto-retry
- Out-of-stock alternatives
- Dynamic recalculation
- Graceful failures

### 5. User Experience ⭐⭐
- Seamless channel switching
- Context preservation
- Natural conversations
- Professional UI

## 📝 Notes for Techathon Presentation

**Key Talking Points:**

1. **Problem:** Fragmented customer experiences cost retailers billions
2. **Solution:** AI orchestrator unifying all touchpoints
3. **Technology:** LangChain + LangGraph for intelligent coordination
4. **Impact:** 15-25% conversion increase, better customer satisfaction
5. **Innovation:** Real-time edge case handling, persistent memory

**Demo Script:**
1. Show mobile app (30 sec)
2. Switch to WhatsApp (45 sec)
3. View store dashboard (30 sec)
4. Run agent monitor with edge cases (60 sec)
5. Highlight key metrics (15 sec)

**Total demo time: ~3 minutes**

## 📞 Support

For issues or questions:
1. Check this README
2. Review inline code comments
3. Check browser console for errors
4. Review backend logs

## 🎉 Congratulations!

You now have a fully functional AI Sales Orchestrator prototype. Good luck with Techathon 6.0! 🚀

---

**Built with ❤️ using LangChain, LangGraph, and Claude AI**