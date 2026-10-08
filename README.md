# AI Sales Orchestrator for Omnichannel Retail

A multi-agent retail system built with **LangGraph**, **LangChain** and **FastAPI** that lets customers shop in natural language and carries their context across channels: mobile web, WhatsApp-style chat, an in-store kiosk and post-purchase follow-up.

> Built for **EY Techathon 6.0** (Semi-Finalist, Top 61 of 185,000+ registrations).

---

## Highlights

- **6 specialized LangGraph agents** (Recommendation, Inventory, Payment, Fulfillment, Loyalty, Support) coordinated by a master orchestrator
- **Parallel agent execution** with `asyncio.gather`: an order modification recalculates stock, offers and totals in about **1.6 seconds**
- **Real-time web chat over WebSockets** with automatic client reconnection and live agent-status streaming
- **Automatic payment failover** across 3 simulated gateways, completing in about 2.7 seconds in the worst case
- **Cross-channel session memory**: likes, cart and conversation history follow the customer from mobile to chat to store
- **Voice input/output** (Web Speech API) and **7 Indian languages** via backend translation

---

## Architecture

```
                 ┌──────────────────────────┐
  Web clients ──►│  FastAPI (REST + WS)      │
  (mobile, chat, │  /api/*   /ws/{session}   │
   kiosk, store) └────────────┬─────────────┘
                              │
                 ┌────────────▼─────────────┐
                 │  LangGraph Orchestrator   │  routes each request,
                 │  (master coordinator)     │  runs agents in parallel
                 └────────────┬─────────────┘
       ┌──────────┬──────────┼──────────┬──────────┬──────────┐
       ▼          ▼          ▼          ▼          ▼          ▼
 Recommendation Inventory  Payment  Fulfillment  Loyalty   Support
                              │
                 ┌────────────▼─────────────┐
                 │  Session Manager          │  persistent cross-channel
                 │  (sessions.json)          │  customer context
                 └──────────────────────────┘
```

| Agent | Responsibility |
|---|---|
| Recommendation | Product suggestions from likes, cart and conversation |
| Inventory | Stock checks across stores, alternatives when out of stock |
| Payment | Transaction processing with gateway failover |
| Fulfillment | Delivery and pickup scheduling |
| Loyalty | Points, offers and bundle discounts |
| Support | Returns, issues and post-purchase help |

---

## How it works

### Orchestration and parallel execution
The orchestrator classifies each request and decides which agents to call. Independent agents run concurrently with `asyncio.gather`, so a cart change triggers Inventory, Loyalty and Payment at once instead of one after another.

```
Change quantity 1 → 2
   ├─ Inventory: check stock     ┐
   ├─ Loyalty:   recalc offers   ├─ in parallel
   └─ Payment:   update total    ┘
   → new discount applied — ~1.6 s total
```

### Payment failover (simulated gateways)
The Payment agent tries gateways in order and falls back automatically on failure. Gateways are **simulated**: each has a configured success rate and timeout, so failover behaviour can be demonstrated without live payment credentials. Replacing a simulated gateway with a real provider (Razorpay, Stripe, etc.) only requires implementing the same call interface.

```
Gateway 1 → FAILED (timeout)
Gateway 2 → FAILED (declined)
Gateway 3 → SUCCESS          ~2.7 s worst case
```

### Real-time updates
Each session opens a WebSocket (`/ws/{session_id}`) that streams chat responses and agent status to the browser. The chat client reconnects automatically if the connection drops.

### Cross-channel memory
Sessions persist likes, cart, conversation history and the active channel, so a customer who likes products on mobile is recognised in chat and at the in-store kiosk.

```json
{
  "session_id": "SESSION_abc123",
  "customer_id": "CUST001",
  "liked_products": ["VH001", "VH002"],
  "cart": [],
  "conversation_history": [],
  "channel": "whatsapp"
}
```

---

## Customer journey

| Step | Page | What happens |
|---|---|---|
| 1 | `mobile.html` | Browse and like products |
| 2 | `chat.html` / `whatsapp.html` | WhatsApp-style chat remembers likes; add to cart, voice and multilingual input |
| 3 | `kiosk.html` | In-store kiosk recognises the customer; try-on reservation, POS checkout |
| 4 | `store-dashboard.html` | Store associate sees the customer's online activity and cart |
| 5 | `agent-monitor.html` | Live agent visualisation and edge-case demos (payment failover, out of stock, order change) |
| 6 | `post-purchase.html` | Order confirmation, tracking and support |

---

## Tech stack

| Layer | Technologies |
|---|---|
| Orchestration | LangGraph, LangChain |
| LLM | Claude API (Anthropic) |
| Backend | FastAPI, Uvicorn, WebSockets, Pydantic |
| Frontend | HTML, CSS, vanilla JavaScript, Web Speech API |
| Translation | googletrans (7 Indian languages) |
| Deployment | AWS EC2, Amazon S3 |

---

## Deployment

The application was deployed on **AWS EC2**, with product catalog and inventory data stored in **Amazon S3**. For local development, the same data is read from `backend/data/`.

See **[AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)** for the full setup: S3 data sync, IAM role, systemd service and Nginx with WebSocket support.

---

## Quick start (local)

```bash
git clone https://github.com/Varsha-1605/AI-Sales-Orchestrator.git
cd AI-Sales-Orchestrator/backend
pip install -r requirements.txt
```

Create `backend/.env`:

```env
ANTHROPIC_API_KEY=your-key
ANTHROPIC_MODEL=claude-sonnet-4-20250514
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
ALLOWED_ORIGINS=http://localhost:3000
```

Run the backend and frontend:

```bash
# Terminal 1
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2
cd frontend && python -m http.server 3000
```

Open `http://localhost:3000/index.html`.

---

## API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/session/create?customer_id=…` | Start a session |
| GET | `/api/session/{session_id}` | Fetch session context |
| POST | `/api/products/like` | Record a liked product |
| GET | `/api/products/recommendations/{session_id}` | Personalised recommendations |
| POST | `/api/cart/add`, `/api/cart/update`, `/api/cart/remove` | Cart operations |
| POST | `/api/store/check`, `/api/store/reserve` | Store availability and try-on reservation |
| POST | `/api/payment/process` | Payment with automatic failover |
| POST | `/api/chat` | Natural-language chat |
| POST | `/api/translate` | Translation (en, hi, mr, gu, ta, te, bn) |
| WS | `/ws/{session_id}` | Real-time chat and agent status |
| GET | `/health` | Health check |

---

## Performance (local)

| Operation | Typical time |
|---|---|
| Agent orchestration | 0.5–2 s |
| AI chat response | 1–3 s |
| Order modification (parallel agents) | ~1.6 s |
| Payment with failover | ~2.7 s worst case |
| WebSocket updates | < 50 ms |

---

## Project structure

```
backend/
  main.py                  FastAPI app, REST + WebSocket endpoints
  graph/                   LangGraph orchestrator and shared state
  agents/                  6 specialised agents + base class
  memory/session_manager.py  cross-channel session persistence
  models/                  Pydantic schemas
  data/                    products, stores, customers, sessions
frontend/                  mobile, chat, WhatsApp-style, kiosk, dashboard, monitor pages
```

---

## Roadmap

- Redis-backed session store for multi-instance deployments
- WhatsApp Business API integration (current channel is a WhatsApp-style web interface)
- Live payment gateway integration
