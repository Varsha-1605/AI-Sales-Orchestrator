<div align="center">

# AI Sales Orchestrator

**Your best salesperson — on WhatsApp, on the website and in the store, all at once.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-multi--agent-1C3C3C)](https://www.langchain.com/langgraph)
[![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Redis](https://img.shields.io/badge/Redis-sessions-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-orders-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![AWS](https://img.shields.io/badge/AWS-EC2-FF9900?logo=amazonaws&logoColor=white)](AWS_DEPLOYMENT.md)

[See it in action](#see-it-in-action) • [Features](#features) • [Why it works](#why-it-works) • [Architecture](#architecture) • [Design decisions](#design-decisions) • [Quick start](#quick-start)

</div>

A good salesperson remembers you. They know what you looked at last week, they check stock before they promise anything, and they never charge your card without asking.

Most retail chatbots do none of this. They forget you the moment you switch from the app to WhatsApp, they answer one question at a time, and they break the moment a payment fails.

**AI Sales Orchestrator behaves like that good salesperson.** One supervisor understands what the customer wants and hands the work to six specialist agents — for products, stock, payment, delivery, offers and support. They share one memory of the customer, so the conversation never starts over.

> [!NOTE]
> Built for **EY Techathon 6.0** — Semi-Finalist, Top 61 of 185,000+ registrations.

## See it in action

Meet Rahul. He needs a formal shirt for an interview on Monday.

1. **On his phone**, he likes two blue shirts and leaves.
2. **That evening on WhatsApp**, he types *"the blue one, size 40, with a matching tie"*. The assistant already knows which blue shirts he means. It checks stock, suggests a tie and applies a bundle discount — all in one reply.
3. **He changes the quantity to 2.** Stock, offers and the total update together in about 1.6 seconds.
4. **He says "buy it".** The assistant shows the final order and waits for his "yes" before taking any payment.
5. **The first payment gateway times out.** Rahul never notices — the system moves to the next gateway and the order goes through.
6. **On Saturday he walks into the store.** The kiosk greets him, shows his order and books a try-on room.

One customer, four touchpoints, zero repeated questions.

## Features

- **Supervisor + 6 specialist agents** — Recommendation, Inventory, Payment, Fulfillment, Loyalty and Support, built as a stateful LangGraph workflow with conditional routing.
- **One cart, every channel** — context follows the customer across WhatsApp, mobile web, chat and the in-store kiosk.
- **Fast live state, safe history** — live sessions and carts in Redis; orders, graph checkpoints and user preferences in PostgreSQL.
- **Human-in-the-Loop checkout** — the graph pauses for customer approval before every transaction.
- **Payment failover** — automatic switch across 3 simulated gateways when one times out or declines.
- **Out-of-stock recovery** — when an item runs out, the system checks nearby stores and suggests similar products instead of losing the sale.
- **Parallel agents** — independent agents run together, so a cart change updates stock, offers and total at once (~1.6 s).
- **Prompt-injection guard** — malicious instructions in chat are blocked before they reach the agents.
- **Real-time UI** — chat replies stream over WebSockets with auto-reconnect, and a monitoring dashboard shows live agent status, execution logs and latency.
- **Fast responses** — session operations under 100 ms and AI replies in 1–3 s, on an async FastAPI backend.
- **Voice and 7 Indian languages** — speech input/output tuned for Indian English, plus translation (en, hi, mr, gu, ta, te, bn).
- **Observable and tested** — LangSmith tracing on every run and 45 automated tests.

## Why it works

| The usual problem | How this project solves it |
|---|---|
| The bot forgets you when you switch channels | One shared customer memory across WhatsApp, web, chat and the store kiosk |
| One big prompt tries to do everything | A supervisor routes each request to the right one of 6 specialist agents |
| Slow, step-by-step replies | Agents that don't depend on each other run at the same time |
| Charging customers without clear consent | Human-in-the-Loop: the workflow pauses for approval before every payment |
| A failed payment means a lost sale | Automatic failover across 3 payment gateways |
| Lost carts after a crash or restart | Live carts in Redis; orders, checkpoints and preferences saved in PostgreSQL |
| Users tricking the bot with clever prompts | Prompt-injection checks before any message reaches the agents |
| "It works on my laptop" | LangSmith tracing on every run, 45 automated tests and a live AWS deployment |

## Architecture

```
   WhatsApp · Mobile web · Chat · Kiosk · Store dashboard
                         │
              ┌──────────▼──────────┐
              │  FastAPI (REST + WS) │
              └──────────┬──────────┘
             ┌───────────▼───────────┐
             │ Supervisor (LangGraph) │ ──► LangSmith tracing
             └───────────┬───────────┘
   ┌────────────┬────────┼────────┬────────────┬─────────┐
   ▼            ▼        ▼        ▼            ▼         ▼
Recommend   Inventory  Payment  Fulfillment  Loyalty   Support
                         │
                 Human approval ──► Gateway 1 → 2 → 3 (failover)
                         │
      ┌──────────────────┴──────────────────┐
      ▼                                     ▼
   Redis                               PostgreSQL
   live sessions, carts                orders, checkpoints, preferences
```

| Agent | Its job |
|---|---|
| Recommendation | Picks products from what the customer liked, added and said |
| Inventory | Checks stock in every store and offers alternatives |
| Payment | Takes payment after approval and switches gateways if one fails |
| Fulfillment | Books home delivery or store pickup |
| Loyalty | Applies points, offers and bundle discounts |
| Support | Handles returns, issues and after-sale questions |

> [!TIP]
> Payment gateways are simulated with set success rates and timeouts, so you can watch failover without real payment keys. To plug in Razorpay or Stripe, implement the same gateway interface.

### How one message flows

1. The customer sends a message from any channel. FastAPI loads their session and cart from Redis.
2. The message is checked for prompt injection. Unsafe messages stop here.
3. The supervisor decides which agents are needed and routes the request.
4. Agents that don't depend on each other run in parallel; their results are merged into one reply.
5. If the request is a purchase, the graph pauses and waits for the customer's approval.
6. After approval, the Payment agent charges through the first working gateway.
7. The order and graph checkpoint are saved in PostgreSQL, and the reply streams back over WebSocket.
8. Every step is traced in LangSmith.

## Design decisions

| Decision | Why |
|---|---|
| Supervisor + specialists, not one big agent | Each agent has a small prompt and a few tools, so it makes fewer mistakes and is easier to test and change on its own. |
| LangGraph instead of a simple agent loop | Saved state, conditional routing, parallel branches and pauses for human approval are built in. |
| Redis for live data, PostgreSQL for history | Carts change on every message and need fast reads; orders and preferences must never be lost. |
| Approval inside the graph, not in the UI | The pause is part of the workflow, so no code path can reach payment without it. |
| Prompt-injection check before routing | Bad input is stopped once, at the entry point, instead of in every agent. |
| Simulated payment gateways | Failover can be tested and shown on demand, without real payment keys. |

## Try every touchpoint

| Page | What to try |
|---|---|
| `mobile.html` | Browse and like products |
| `whatsapp.html` / `chat.html` | Shop by text, voice or in Hindi — your likes are already there |
| `kiosk.html` | Walk "into the store": get recognised, book a try-on, check out |
| `store-dashboard.html` | See the customer through the store staff's eyes |
| `agent-monitor.html` | Watch the agents work live and trigger payment failures or stock-outs |
| `post-purchase.html` | Track the order and ask for help |

## Tech stack

| Layer | Tools |
|---|---|
| Agents | LangGraph, LangChain, Claude (Anthropic) |
| Backend | FastAPI, Uvicorn, WebSockets, Pydantic |
| Data | Redis, PostgreSQL |
| Observability and testing | LangSmith, pytest |
| Frontend | HTML, CSS, JavaScript, Web Speech API |
| Deployment | AWS EC2, Amazon S3, Nginx |

## Quick start

> [!IMPORTANT]
> You need Python 3.11+, a running Redis and PostgreSQL instance, and an Anthropic API key.

```bash
git clone https://github.com/Varsha-1605/AI-Sales-Orchestrator.git
cd AI-Sales-Orchestrator/backend
pip install -r requirements.txt
```

Create `backend/.env`:

```env
ANTHROPIC_API_KEY=your-key
ANTHROPIC_MODEL=claude-sonnet-4-20250514
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://user:password@localhost:5432/sales
LANGSMITH_API_KEY=your-key
LANGSMITH_TRACING=true
ALLOWED_ORIGINS=http://localhost:3000
```

Start the backend and frontend in two terminals:

```bash
cd backend && uvicorn main:app --reload --port 8000
cd frontend && python -m http.server 3000
```

Open http://localhost:3000/index.html.

Run the tests:

```bash
cd backend && pytest
```

## Deployment

Runs on **AWS EC2** behind Nginx (with WebSocket support), with catalog and inventory data in **Amazon S3**. Full steps — S3 sync, IAM role, systemd service and Nginx — are in [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md).

## Project structure

```
backend/
  main.py           FastAPI app: REST and WebSocket endpoints
  graph/            LangGraph supervisor and shared state
  agents/           6 specialist agents and their base class
  memory/           session handling
  models/           Pydantic schemas
  data/             products, stores, customers
frontend/           mobile, WhatsApp, chat, kiosk, dashboard and monitor pages
```

## Author

**Varsha Dewangan** — AI Engineer building multi-agent systems, RAG pipelines and voice agents.
[LinkedIn](https://linkedin.com/in/varsha-dewangan-197983256) · [GitHub](https://github.com/Varsha-1605)
