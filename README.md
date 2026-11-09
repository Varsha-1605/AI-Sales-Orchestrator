<div align="center">

# AI Sales Orchestrator

**Your best salesperson — on WhatsApp, on the website and in the store, all at once.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-multi--agent-1C3C3C)](https://www.langchain.com/langgraph)
[![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Redis](https://img.shields.io/badge/Redis-sessions-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-orders-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](DEPLOYMENT.md)

[Watch the demo](#watch-the-demo) • [See it in action](#see-it-in-action) • [Features](#features) • [Why it works](#why-it-works) • [Architecture](#architecture) • [Performance](#performance) • [Evaluation](#evaluation) • [Built for production](#built-for-production) • [Design decisions](#design-decisions) • [Quick start](#quick-start)

</div>

A good salesperson remembers you. They know what you looked at last week, they check stock before they promise anything, they tell you the real price before you pay, and they never charge your card without asking.

Most retail chatbots do none of this. They forget you the moment you switch from the app to WhatsApp, they answer one question at a time, and they break the moment a payment fails.

**AI Sales Orchestrator behaves like that good salesperson.** One supervisor understands what the customer wants and hands the work to six specialist agents — for products, stock, payment, delivery, offers and support. They share one memory of the customer, so the conversation never starts over. The same assistant even talks to the store: when a customer reserves a try-on or pays for a pickup, the associate on the shop floor is alerted and answers with one tap.

> [!NOTE]
> Built for **EY Techathon 6.0** — Semi-Finalist, Top 61 of 185,000+ registrations.

## Watch the demo

<div align="center">

[![Watch the full demo — 3 min 44 s](video/demo_preview.gif)](video/agentic_ai_video.mp4)

**[▶ Watch the full 3 min 44 s walkthrough](video/agentic_ai_video.mp4)** — from the first like on a phone to the order follow-up.

</div>

## See it in action

Meet Rahul. He needs a formal shirt for an interview on Monday.

1. **On his phone**, he likes two shirts and leaves.
2. **That evening on WhatsApp**, the assistant greets him by name and already knows which items he liked. It checks real stock in all four stores, suggests a matching tie and shows him exactly what he will pay, line by line.
3. **He changes the quantity to 2.** Stock, offers and the total update together in about 1.6 seconds.
4. **He reserves a try-on at the Powai store.** The store associate sees the request on the staff dashboard, accepts it, and Rahul gets the confirmation in the same WhatsApp chat.
5. **He says "buy it".** The assistant shows the final order and waits for his "yes" before taking any payment.
6. **The first payment gateway times out.** Rahul never notices — the system moves to the next gateway and the order goes through. The Powai associate is told the order is paid and that Rahul is coming to collect it.
7. **On Saturday he walks into the store.** The kiosk greets him, shows his reserved items and completes the pickup. Afterwards the order page shows his timeline, invoice and returns.

One customer, five touchpoints, zero repeated questions.

## Features

- **Supervisor + 6 specialist agents** — Recommendation, Inventory, Payment, Fulfillment, Loyalty and Support, built as a stateful LangGraph workflow with conditional routing.
- **One cart, every channel** — context follows the customer across WhatsApp, mobile web, chat and the in-store kiosk.
- **Honest pricing** — the backend is the only place a price is worked out. Every channel shows the same breakdown (items, offer, loyalty points, total to pay), and the approval question and the payment charge the exact same figure. Loyalty points are never taken silently: the customer chooses to use them.
- **Fast live state, safe history** — live sessions and carts in Redis; orders, graph checkpoints and user preferences in PostgreSQL.
- **Human-in-the-Loop checkout** — the graph pauses for customer approval before every transaction.
- **Payment failover** — automatic switch across 3 simulated gateways when one times out or declines, completing in about 2.7 seconds in the worst case.
- **Out-of-stock recovery** — a sold-out item is labelled as such, cannot be added to the cart, and the system suggests similar items that are in stock instead of losing the sale.
- **Store associate in the loop** — reserving a try-on or paying for a pickup alerts the associate on the staff dashboard, who accepts or declines; the customer is told the answer in their chat.
- **Parallel agents** — independent agents run together, so a cart change updates stock, offers and total at once (~1.6 s).
- **Prompt-injection guard** — malicious instructions in chat, including disguised and Hinglish variants, are blocked before they reach the agents.
- **Replies that start immediately** — answers stream word by word while the customer sees which agent is working. A monitoring dashboard shows live agent status, execution logs, payment attempts and latency over WebSockets with auto-reconnect.
- **Fast responses** — session operations under 100 ms and AI replies in 1–3 s, on an async FastAPI backend with startup warm-up so the first customer never pays for a cold start.
- **Voice and 7 Indian languages** — speech input/output tuned for Indian English, plus translation (en, hi, mr, gu, ta, te, bn).
- **Two AI providers** — Claude first, with an automatic OpenAI fallback if a call fails. It also runs without any API key, using keyword routing and template replies, so anyone can try it in minutes.
- **Measured, not guessed** — **98% routing accuracy** over 300+ turns, **96% task completion** on 50 multi-turn conversations and **98% of prompt-injection attacks blocked**, backed by golden datasets you can re-run.
- **Observable and tested** — LangSmith tracing on every run, Prometheus metrics and 73 automated tests.
- **A storefront that looks like a product** — a consistent design system across all eight screens (mobile, WhatsApp, web chat, kiosk, staff dashboard, agent monitor, order follow-up), with product photos, accessible contrast and real error and empty states.

## Why it works

| The usual problem | How this project solves it |
|---|---|
| The bot forgets you when you switch channels | One shared customer memory across WhatsApp, web, chat and the store kiosk |
| One big prompt tries to do everything | A supervisor routes each request to the right one of 6 specialist agents |
| Slow, step-by-step replies | Agents that don't depend on each other run at the same time, and replies stream as they are written |
| Charging customers without clear consent | Human-in-the-Loop: the workflow pauses for approval before every payment |
| A total that changes between screens | One server-side price used by every channel, the approval and the charge |
| A failed payment means a lost sale | Automatic failover across 3 payment gateways |
| Selling something that is out of stock | Stock is checked before an item enters the cart, with in-stock alternatives offered |
| Online and in-store feel like different companies | Reservations and pickups reach the store associate in real time |
| Lost carts after a crash or restart | Live carts in Redis; orders, checkpoints and preferences saved in PostgreSQL |
| Users tricking the bot with clever prompts | Prompt-injection checks before any message reaches the agents |
| "It works on my laptop" | LangSmith tracing, 73 automated tests, evals, Docker and CI |

## Architecture

```
   WhatsApp · Mobile web · Chat · Kiosk · Store dashboard
                         │
              ┌──────────▼──────────┐
              │  FastAPI (REST + WS) │  tokens · rate limits · metrics
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
   live sessions, carts, alerts        orders, checkpoints, preferences
```

| Agent | Its job |
|---|---|
| Recommendation | Picks products from what the customer liked, added and said |
| Inventory | Checks stock in every store and offers alternatives |
| Payment | Takes payment after approval and switches gateways if one fails |
| Fulfillment | Books home delivery or store pickup |
| Loyalty | Works out offers, bundle discounts and the points the customer can use |
| Support | Handles returns, issues and after-sale questions |

> [!TIP]
> Payment gateways are simulated with set success rates and timeouts, so you can watch failover without real payment keys. To plug in Razorpay or Stripe, implement the same gateway interface.

### How one message flows

1. The customer sends a message from any channel. FastAPI checks their session token and rate limit, then loads their session and cart from Redis.
2. The message is checked for prompt injection. Unsafe messages stop here.
3. The supervisor decides which agents are needed and routes the request.
4. Agents that don't depend on each other run in parallel; their results are merged into one reply, which streams back to the customer.
5. If the request is a purchase, the graph pauses and waits for the customer's approval.
6. After approval, the Payment agent charges the server-side total through the first working gateway.
7. The order and graph checkpoint are saved in PostgreSQL, and the store associate is alerted if the customer is collecting in store.
8. Every step is traced in LangSmith and counted in Prometheus.

## Performance

Typical times on a local machine:

| Operation | Typical time |
|---|---|
| Session creation | < 100 ms |
| Product like | < 50 ms |
| Agent orchestration | 0.5–2 s |
| AI chat response | 1–3 s |
| Order modification (parallel agents) | ~1.6 s |
| Payment with failover | ~2.7 s worst case |
| WebSocket updates | < 50 ms |

Replies also start appearing at once: the customer sees which agent is working and the text streams in as it is written, so the wait feels shorter than the totals above.

## Evaluation

The assistant is scored on three things that decide whether customers can trust it.

| Eval | Result | What it measures | Data |
|---|---|---|---|
| Routing accuracy | **98%** | The supervisor sends each message to the right agents, including Hinglish, typos and messages with several intents | 300+ labelled turns |
| Task completion | **96%** | A full conversation reaches its goal: checkout, a delivery answer, an out-of-stock recovery | 50 multi-turn conversations |
| Prompt-injection defence | **98%** | Attacks are blocked before any agent runs, while normal messages still go through | 40 attacks and 20 normal messages |

Re-run them any time. Reports with every failure are saved in `evals/results/`:

```bash
uv run python -m evals.run_evals
```

The datasets are in `goldens/`. Each case is labelled by hand, so a failure shows exactly which message was misrouted or which attack got through.

## Built for production

This project is written the way a team would ship it, even though it has not been deployed anywhere yet. Everything below is in the code and is covered by tests or documented steps.

| Area | What is in place |
|---|---|
| Security | Per-session tokens on every REST route and WebSocket (`AUTH_ENABLED`), server-side prices (a page can never set its own price), validated and length-limited input, restricted CORS |
| Payments | Idempotency keys so a retried request never charges twice, a payment that is consumed once per order, and a human approval before every charge |
| Reliability | Timeouts and retries on every model call, Claude to OpenAI fallback, startup retries for Redis and PostgreSQL, a `/health` check that reports both, safe concurrent cart edits |
| Abuse control | Per-client rate limiting and a prompt-injection guard that normalises disguised text before checking it |
| Observability | Request ids on every log line, optional JSON logs, Prometheus `/metrics`, LangSmith tracing |
| Data | Numbered SQL migrations with a lock, so tables can change safely later |
| Packaging | `Dockerfile` (non-root, health check), `docker-compose.yml` for Redis and PostgreSQL, a GitHub Actions workflow that runs the tests and builds the image |
| Quality | 73 automated tests, plus evals for routing, task completion and prompt injection |

## Design decisions

| Decision | Why |
|---|---|
| Supervisor + specialists, not one big agent | Each agent has a small prompt and a few tools, so it makes fewer mistakes and is easier to test and change on its own. |
| LangGraph instead of a simple agent loop | Saved state, conditional routing, parallel branches and pauses for human approval are built in. |
| Redis for live data, PostgreSQL for history | Carts change on every message and need fast reads; orders and preferences must never be lost. |
| Approval inside the graph, not in the UI | The pause is part of the workflow, so no code path can reach payment without it. |
| One server-side price | Pages can show anything, but the amount charged is always recomputed from the catalog, so what the customer sees and what they pay cannot drift apart. |
| Loyalty points are opt-in | A customer's points are theirs to spend. Using them silently makes a total look wrong and erodes trust. |
| Prompt-injection check before routing | Bad input is stopped once, at the entry point, instead of in every agent. |
| Simulated payment gateways | Failover can be tested and shown on demand, without real payment keys. |

## Try every touchpoint

| Page | What to try |
|---|---|
| `mobile.html` | Browse and like products |
| `whatsapp.html` / `chat.html` | Shop by text, voice or in Hindi — your likes are already there. Add to cart, use loyalty points, reserve a try-on, check out |
| `kiosk.html` | Walk "into the store": get recognised, see your reserved store, complete the pickup |
| `store-dashboard.html` | See the customer through the store staff's eyes, and accept or decline reservations and pickups |
| `agent-monitor.html` | Watch the agents work live and trigger payment failures, stock-outs or an injection attack |
| `post-purchase.html` | Track the order, see the invoice, start a return and ask for help |

## Tech stack

| Layer | Tools |
|---|---|
| Agents | LangGraph, LangChain, Claude (Anthropic) with OpenAI fallback |
| Backend | FastAPI, Uvicorn, WebSockets, server-sent events, Pydantic |
| Data | Redis, PostgreSQL |
| Observability and testing | LangSmith, Prometheus, pytest |
| Frontend | HTML, CSS, JavaScript, Web Speech API |
| Packaging | uv, Docker, GitHub Actions |

## Quick start

> [!IMPORTANT]
> You need Python 3.11+, [uv](https://docs.astral.sh/uv/) and Docker (for Redis and PostgreSQL). API keys are optional: with none, the assistant uses keyword routing and template replies.

```bash
git clone https://github.com/Varsha-1605/AI-Sales-Orchestrator.git
cd AI-Sales-Orchestrator
docker compose up -d          # Redis and PostgreSQL
uv sync                       # install dependencies
cp .env.example .env          # then add your keys, if you have them
```

The most useful settings in `.env`:

```env
ANTHROPIC_API_KEY=your-key        # optional; the first model tried
OPENAI_API_KEY=your-key           # optional; used if Claude fails
REDIS_URL=redis://localhost:6379/0
POSTGRES_URL=postgresql://sales:sales@localhost:5432/sales
LANGSMITH_API_KEY=your-key        # optional tracing
AUTH_ENABLED=false                # set to true to require session tokens
```

Start the backend and the frontend in two terminals:

```bash
uv run python main.py
cd frontend && python -m http.server 3000
```

Open http://localhost:3000/index.html and click **Start fresh** for a clean run.

Run the tests and the evals:

```bash
uv run pytest
uv run python -m evals.run_evals
```

## Deploying it

The project is not deployed yet, but it is ready to be. `DEPLOYMENT.md` covers running it with Docker and the production settings (secrets, tokens, rate limits, health checks). `AWS_DEPLOYMENT.md` is a step-by-step guide for an EC2 instance behind Nginx with WebSocket support, with the catalog data in Amazon S3.

## Project structure

```
main.py                 FastAPI app: startup, health, metrics
ai_workflow/
  api/                  REST endpoints
  channels/             WhatsApp/web/kiosk entry point, WebSocket and streaming
  graph/                LangGraph workflow: supervisor, approval, shared state
  agents/               the 6 specialist agents
  tools/                catalog, cart, pricing and order functions the agents call
  integrations/         payment gateways with failover, translation
  storage/              Redis sessions, PostgreSQL orders and migrations, catalog data
  guardrails.py         prompt-injection checks
  llm.py                Claude with OpenAI fallback
  settings.py           every setting, read from the environment
data/                   products, stores, customers
frontend/               the eight screens and their shared design system
tests/                  73 automated tests
evals/ goldens/         routing, task-completion and injection evals with their datasets
video/                  demo walkthrough
```

## Author

**Varsha Dewangan** — AI Engineer building multi-agent systems, RAG pipelines and voice agents.
[LinkedIn](https://linkedin.com/in/varsha-dewangan-197983256) · [GitHub](https://github.com/Varsha-1605)
