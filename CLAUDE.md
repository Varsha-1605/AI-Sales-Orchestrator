# Restructure progress

Plan: `restructure_plan.md`. Work one step at a time, in order. Read this file first in a new session and continue from the first unticked step.

- [x] Step 1 — Setup files
  - Written: pyproject.toml, docker-compose.yml, .env.example, .gitignore (merged); removed backend/requirements.txt; branch `restructure` created.
- [x] Step 2 — Move files
  - Moved with git mv: main.py, ai_workflow/{settings,schemas}.py, ai_workflow/agents/*, ai_workflow/graph/*, data/*.json; git rm'd sessions.json, memory/, models/, backend/.gitignore; added ai_workflow/__init__.py; imports changed to `ai_workflow.…` (main.py's session import points at the Step 4 file for now).
- [x] Step 3 — settings.py and schemas.py
  - Rewritten: ai_workflow/settings.py, ai_workflow/schemas.py (unused models removed; USE_MOCK_RESPONSES removed — base_agent will check the key directly in Step 6).
- [x] Step 4 — Storage
  - Written: ai_workflow/storage/{__init__,catalog_store,redis_store,postgres_store}.py, migrations/001_initial.sql (was schema.sql; see "Production hardening") (redis_store also has `ping_redis()` for the startup check in main.py).
- [x] Step 5 — Tools and payments
  - Written: ai_workflow/tools/{__init__,catalog,cart,orders}.py, ai_workflow/integrations/{__init__,translation}.py, ai_workflow/integrations/payments/{__init__,base,gateways,charge}.py.
- [x] Step 6 — Agents
  - Rewritten: ai_workflow/agents/{base_agent,recommendation_agent,inventory_agent,payment_agent,fulfillment_agent,loyalty_agent,support_agent,__init__}.py.
- [x] Step 7 — Guardrails
  - Written: ai_workflow/guardrails.py.
- [x] Step 8 — Graph
  - Written/changed: ai_workflow/graph/{state,supervisor,approval,orchestrator_graph}.py.
- [x] Step 9 — Channels, API and main.py
  - Written: ai_workflow/channels/{__init__,websocket_manager,base,web}.py, ai_workflow/api/{__init__,routes}.py, main.py; changed frontend/chat.html (live /api/chat call with fallback, approval buttons, `sendApproval`).
- [x] Step 10 — Tests
  - Written (45 test functions, not run): tests/conftest.py, tests/agents/test_agent_results.py (9), tests/graph/test_graph_flow.py (9), tests/tools/test_tools.py (6), tests/integrations/test_payment_failover.py (5), tests/storage/test_redis_store.py (4) + test_postgres_store.py (2, integration), tests/channels/test_handle_message.py (3), tests/api/test_routes.py (4), tests/test_guardrails.py (3).
- [x] Step 11 — Evals and goldens
  - Written (not run, no scores): evals/{__init__,common,run_evals,eval_routing,eval_task_completion,eval_prompt_injection}.py; goldens/{routing_goldens (340 turns),conversation_goldens (50),injection_goldens (40 attacks + 20 normal)}.json.
- [x] Step 12 — Docs
  - Changed: DEPLOYMENT.md, AWS_DEPLOYMENT.md (README.md untouched).
- [x] Step 13 — Final self-check
  - Read-only checks done: all `ai_workflow.*` imports and imported names exist; every endpoint in the contract table is in api/routes.py, channels/web.py or main.py; every setting used is in settings.py and .env.example; nothing imports `config`, `memory` or `models`; `backend/` is gone; README.md has no diff; only frontend/chat.html changed in frontend/.

## Questions

## Differences from the plan
- Step 1: kept `FASTAPI_HOST`, `FASTAPI_PORT`, `DEBUG_MODE` in `.env.example` (main.py's `uvicorn.run` block needs them). pyproject also has `pythonpath = ["."]`, `asyncio_mode = "auto"` and `[tool.uv] package = false` so tests import `ai_workflow` and async tests run without an install step. `.gitignore` also ignores `data/sessions.json` as the plan's directory listing says.
- Step 4: `create_session` copies liked_products, cart, conversation_history and reserved_store from the customer's latest session (my reading of "the cart follows the customer"). `get_stock` matches inventory keys "Bandra" to store name "Bandra Store" and returns 0 when a product has no inventory. `cart/add` appends a line each time (as before, no merging).
- Step 5: added `nearby_stores(location)` to `tools/catalog.py` (used by `check_stock` and `delivery_options`, avoids duplicating the store filter). `check_stock` returns a `stores` list `[{name, distance, stock}]` so `/api/store/check` can use it directly. `loyalty_discount` gives 0 points to a customer not in customers.json (old code defaulted to 500). `create_order` stores the raw session cart lines as `items`; the kiosk route will pass its own items in a session copy. `GATEWAYS` (name → instance) in gateways.py is what `charge` reads; tests can replace entries to force failures. The `/api/translate` "text is required" 400 check stays in the route.
- Data gap: only VH001 and VH001B have `inventory` in products.json, so every other product shows 0 stock. Add inventory to products.json to fix; not done here.
- Step 6: the recommendation agent's result is the list of recommendations itself (`result_key="recommendations"`, as `synthesize` and `AgentState` already expect a list), so the old `total_found` field is dropped. `_call_llm` takes an optional `fallback` (used for the template reasoning); `_format_json_response` and `_load_data` removed (unused). Call records no longer carry the agent's result (it lives under `result_key`). Inventory "store"/"nearby" requests now use `check_stock` (the old code returned a bare list that could not be stored in state), and the cart-wide check returns `available` instead of `all_available` so `synthesize` reads it correctly. The payment agent no longer re-checks keywords: it charges whenever the supervisor chose it and the customer approved. Gateway attempts from the agent are not pushed over WebSocket (only the `/api/payment/process` route does that) because a callback cannot be kept in checkpointed state.
- Step 8: `messages` and `agent_calls` in `AgentState` no longer use `add` reducers. With a checkpointer the saved thread state is merged with each new input, so `add` would pile up the session history and old agent calls every turn; `create_initial_state` resets every key each turn instead, and `call_agents_node` merges the call records itself. `choose_agents` is `async` (it may call the LLM). `simple_response` now goes to END instead of `synthesize`, because `synthesize` overwrote the greeting with its default text. The `pending_approval` state field exists as the plan says, but the pending approval itself is read from the interrupt by `handle_message`; no node writes the field. `ask_for_approval` skips the question when the cart is empty (nothing would be charged). `visualize_graph` removed (unused debug helper). `synthesize` adds a "payment cancelled, cart saved" line when `next_action == "payment_cancelled"`.
- Step 9: `websocket_manager.py` also defines the shared `manager` instance. `agent_called` WebSocket messages are sent after the graph run (one per agent call record), not live while agents run. Errors from the graph return a fixed apology without the exception text (old code returned `str(e)`). `/api/cart/update` no longer sleeps between its two demo WebSocket messages. `main.py` sets the Windows selector event loop policy so the Postgres driver works on Windows. `/api/chat/approve` with nothing paused returns a "nothing waiting for your approval" reply. `/api/translate` runs the blocking translate call in a thread. In `chat.html`, the live reply maps `product_id` to `id` for the product cards and the page sends the English-translated message to the backend.
- Step 10: instead of `FakeListChatModel`, tests set every agent's `llm` and `supervisor.llm` to `None` (keyword routing, template text); the supervisor's LLM path is tested with a small fake router object that returns an `AgentChoice`. Test files have unique names and the test folders have no `__init__.py`. The two Postgres tests skip themselves when `POSTGRES_URL` is empty. Two of the plan's 9 graph tests are my additions (greeting reply; results under their keys with no duplicate calls).
- Step 11: conversations have an optional `cart` field (list of product ids) because the graph cannot add items to a cart (that is a REST call). Routing goldens label what a good router should return (intent agents plus loyalty), not what the keyword rules return, so the keyword fallback is expected to miss Hinglish, typo and some multi-intent turns. `injection_goldens.json` is an object with `attacks` and `normal` lists. Each eval exposes `async run_eval()`; `run_evals.py` saves the JSON reports to `evals/results/` and prints the table. Run from the repo root: `uv run python -m evals.run_evals` (plain `python` uses the global install and can fail on mismatched LangChain versions).
- Step 12: the docs use `uv` (`uv sync`, `uv run`) for installs, since `pyproject.toml` replaces `requirements.txt`. AWS guide: Redis and PostgreSQL are installed on the same EC2 instance (the app now needs both), the `--exclude sessions.json` flag is dropped (the file no longer exists), and the systemd unit waits for both services. DEPLOYMENT.md: removed the dead `USE_MOCK_RESPONSES` lines and the `backend/logs/app.log` tip (no log file exists).
- Nothing was run, tested, installed or built, so every file is unverified. No `uv.lock` exists yet. `restructure_plan.md` and this file are untracked; nothing is committed.
- Added after the plan: OpenAI fallback. `ai_workflow/llm.py` (`build_llm`) tries Anthropic first, then OpenAI; each is used only if its key is set. `base_agent.py` and `supervisor.py` use it. New settings `OPENAI_API_KEY`, `OPENAI_MODEL` (settings.py, .env.example); new dependency `langchain-openai` (pyproject.toml). Existing tests still work because they set `llm` to `None`/a fake.
- Dependency fix: `googletrans==4.0.0rc1` pins `httpx==0.13.3`, which cannot be installed together with `langchain-anthropic`/`langchain-core` (they need `httpx>=0.23`). Changed to `googletrans>=4.0.2`, whose `translate` is async, so `integrations/translation.py::translate` is now `async` and `/api/translate` awaits it (the earlier `asyncio.to_thread` is gone). Python stays at 3.11 (`requires-python >=3.11`); the version was not the cause.
- Demo-video frontend work (after the plan): `frontend/config.js` now holds `API_URL`/`WS_URL` (all 8 pages load it; AWS/DEPLOYMENT docs updated). `agent-monitor.html` rewritten to show real WebSocket events (agent status, payment gateway failover, approval prompt with Approve/Reject, guardrail blocks) and its 5 scenario buttons call the real API. `whatsapp.html` reads the shared cart from the backend, sends payment/offer/return/delivery/other messages to `/api/chat` with `channel: whatsapp`, and has Yes/No approval buttons; its old scripted checkout/delivery/coupon replies (`delivery_options`, `apply_coupon`, `express_delivery`, `standard_delivery` cases) are no longer reachable from the checkout button. `chat.html` reloads the backend cart and shows a "blocked by guardrail" notice. Backend: new `GET /api/cart/{session_id}` (names, prices, total); `ConnectionManager` now keeps a list of sockets per session so chat and monitor can watch the same session; `channels/base.py` streams live `agent_called` events (processing/success/failed), sends `input_blocked`, returns `blocked` in the reply, and empties the cart after a paid order. Two tests added (47 total): paid order empties cart, cart endpoint.
- Names kept from the plan/existing code though jargon-like: `orchestrator_graph.py`, `supervisor.py`, `base_agent.py` (suggested plain names: `chat_graph.py`, `agent_picker.py`, `agent_base.py`).

## Production hardening (after the plan)

Nothing below has been run. All of it is checked by reading only. The first job in a new session is to run `uv run pytest` and fix what fails (62 tests now), then `python -m evals.run_evals`.

Done:
- **Session tokens (auth):** `create_session` makes a secret token returned by `/api/session/create` as `token`. With `AUTH_ENABLED=true` every route and the WebSocket require it (`X-Session-Token` header, or `?token=` for the socket); compared with `secrets.compare_digest`. Default is `false` so the demo works without it; set it to `true` in production. `GET /api/session/{id}` hides the token. `frontend/config.js` wraps `fetch` to send the token and offers `socketUrl()`; `index.html` and the monitor store it.
- **Server-side money:** `/api/payment/process` ignores the client `amount` and charges the discounted cart total (400 if the cart is empty); a successful charge is saved as `session.last_payment`. `/api/order/complete` needs that payment (402 otherwise), takes items and total from the server, and uses the payment once, so a repeat cannot create a second order. `kiosk.html` now calls `payment/process` before `order/complete`.
- **Idempotency:** optional `Idempotency-Key` header on `/api/payment/process` returns the first result on a retry (stored 24h in Redis). Double approval of a paused payment was already harmless (`resume_after_approval` finds nothing paused).
- **Rate limiting:** Redis counter per client IP per minute (`RATE_LIMIT_PER_MINUTE`, default 60) on session create, chat, approve, payment, order complete, translate and recommendations; returns 429.
- **LLM timeouts and retries:** `LLM_TIMEOUT_SECONDS` (20) and `LLM_MAX_RETRIES` (2) on both Anthropic and OpenAI models.
- **Startup and health:** Redis and Postgres are retried 5 times (2s apart) before the app gives up; a failed Postgres open closes its pool. `/health` returns 503 unless Redis (and Postgres, if configured) answer and reports each one. Postgres reconnects are handled by the pool, Redis by the client.
- **Safe concurrent session writes:** `redis_store.update_session` uses WATCH/MULTI with retry; cart, likes, reserve and conversation saving use it. Conversation history is capped at 100 entries.
- **Validation:** message length 1-1000, quantity 1-99, size max 10 characters, rating 1-5, translate text max 2000; unknown product (cart add, like, store check), unknown store (reserve) and unknown customer (session create) are rejected.
- **Guardrail:** messages are normalized (NFKC, invisible characters removed, spacing collapsed) and more paraphrase and Hinglish patterns were added. Still regex-based, so it will miss novel phrasings.
- **CORS:** methods limited to GET, POST, OPTIONS; headers to Content-Type, X-Session-Token, Idempotency-Key, X-Request-ID.
- **Logging and metrics:** a request id on every log line and response (`X-Request-ID`), `LOG_JSON` for JSON logs, request log line with status and time, Prometheus `/metrics` (new dependency `prometheus-client`).
- **Migrations:** `storage/schema.sql` became numbered files in `storage/migrations/` run by `open_postgres` with a `schema_migrations` table and an advisory lock, so tables can change safely later. Add `002_...sql` for each change.
- **Docker and CI:** `Dockerfile` (non-root user, health check), `.dockerignore`, `.github/workflows/ci.yml` (pytest without integration tests, then docker build). DEPLOYMENT.md has the commands.
- **Data:** every product now has inventory in all 4 stores (made with a one-off script, values are made-up demo numbers). `VH002` is sold out everywhere on purpose for the out-of-stock demo. `get_stock` uses the product's first size when the requested size is not one it comes in (ties, socks, belts).
- **Secrets:** documented in DEPLOYMENT.md (environment variables filled from a secret store); no code change was needed.
- **Tests added:** payment needs server price and is idempotent, empty-cart payment rejected, unknown product and bad quantity rejected, order needs a payment, token required when `AUTH_ENABLED`, 429 on too many requests, `/health`, rate-limit counter, guardrail hidden characters and Hinglish (9 new; the order-complete test was rewritten).

Not done (on purpose or not possible):
- **Real payment gateways** stay simulated (you said no integrations).
- **Tests and evals have never been run**, so there are no pass/fail results and no scores.
- No admin screen or API to edit the catalog (it is still read-only JSON in `data/`).
- Guardrail is not LLM-based; there is no CAPTCHA or per-customer (as opposed to per-IP) rate limit.
- `AUTH_ENABLED` is `false` by default; the token flow in the frontend is untested.

## Frontend design

Status: **all 8 pages redesigned** (index, chat, whatsapp, mobile, kiosk, store-dashboard, agent-monitor, post-purchase). Wordmark is the project name, "Orchestrator" (placeholder until a real brand asset exists). Icons live in `frontend/icons.svg`. Fonts load from Google Fonts. Pages are redesigned one at a time; see the checklist.

### Direction: premium retail, built as a system

The reference is a large menswear retailer's own product: ivory and ink, one accent, thin lines, generous space, a strict grid and editorial typography. Nothing is decorative for its own sake. It has to look like a company serving millions of customers: consistent, calm, accessible, and complete (every state designed, not only the happy path). No themed craft touches, no gimmicks, no "demo" language in the interface.

### Palette (CSS variables in `styles.css`)

| Variable | Value | Used for |
|---|---|---|
| `--ivory` | `#F5F2EC` | page background |
| `--white` | `#FFFFFF` | panels, inputs, store chat bubbles |
| `--stone` | `#E7E2D8` | alternate rows, subtle fills, skeleton loaders |
| `--line` | `#D6D0C3` | 1px borders and dividers |
| `--ink` | `#16212A` | text, primary buttons, headers (deep navy-charcoal, no violet) |
| `--ink-soft` | `#55616A` | secondary text (contrast 5.9:1 on ivory) |
| `--accent` | `#82632B` | the one accent: links, active states, focus ring, key numbers |
| `--decision` | `#7A2B2B` | only for "needs your decision" (approval prompts, destructive) |
| `--success` | `#2F6B4F` | in stock, paid, confirmed |
| `--danger` | `#B3392B` | failed, out of stock, blocked |
| `--night`, `--night-panel`, `--night-line` | `#12171B`, `#1A2126`, `#2A333A` | agent monitor only (dark technical view) |

Every text and background pair meets WCAG AA (4.5:1). Status colours are never the only signal: each status also has a word and an icon.

### Fonts (Google Fonts)

- **Headlines: Newsreader** (opsz variable, 400 and 500, italic for emphasis): page titles, product names, large prices. A restrained editorial serif, used sparingly.
- **UI and body: Instrument Sans** (400, 500, 600): navigation, buttons, forms, chat, tables. 15-16px, 1.5 line height.
- **Data: IBM Plex Mono** (400, 500): prices in tables, order and session ids, timestamps, the agent monitor. Tabular numerals everywhere money is shown.
- Fallbacks when offline: `Georgia`, `Helvetica Neue`, `Menlo`.

### Design system tokens

- Spacing on a 4px grid: 4, 8, 12, 16, 24, 32, 48, 64 (`--space-1` to `--space-8`).
- Type scale: 12 / 14 / 16 / 20 / 28 / 40 / 56 (`--text-xs` to `--text-3xl`), with the kiosk using the next step up.
- Radius: 2px for controls and panels, nothing larger. No shadows; separation comes from 1px lines and background steps (ivory, white, stone).
- Motion: 120-180ms opacity and color changes only; all motion removed under `prefers-reduced-motion`.
- Breakpoints: 480, 768, 1100, 1440. Content max width 1200px on desktop, 100% on mobile with 16px gutters.

### Rules for layout and components

1. **One grid, one shell.** Every page (except the kiosk and the WhatsApp screen) shares an app bar: wordmark at left, section name, then the session reference in mono at right, over a 1px line. Content sits on a 12-column grid with fixed gutters. Page title is a Newsreader headline with a small uppercase mono label above it.
2. **Components are complete.** Buttons (primary solid ink, secondary outlined, quiet text, destructive in `--decision`) all have default, hover, `:focus-visible` (2px accent ring, 2px offset), active, disabled and loading states. Inputs have label, hint and error states. Tables and lists have hover rows, empty states and skeleton loading rows in `--stone`. Status uses one badge style: outlined, uppercase mono label with a small icon, in success, danger, accent or ink-soft.
3. **Products and money.** Products are list rows or a clean image-led grid with a fixed aspect ratio, name in Newsreader, price in mono, size and stock as quiet text, one clear action. Totals use a right-aligned mono summary block with a ruled total line. Trust cues are visible where money moves: "Secure payment", order reference, delivery estimate, return window.
4. **Each page scales to its job.** Kiosk: one task per screen, type one step up, 64px touch targets, high contrast, no hover reliance. Staff dashboard: dense 13px rows, sticky header, sortable-looking columns, status badges, no decoration. WhatsApp: keeps the platform's conventions (green-tinted header in `--success`, patterned wallpaper in ivory tones, bubbles with tails, ticks, input bar), refined. Agent monitor: the only dark page, mono, an engineering console with a clear event timeline. Mobile: one column, 16px gutters, sticky bottom action bar. Web chat and post-purchase: roomy and editorial on ivory.
5. **Accessibility and trust.** Semantic landmarks, visible focus, 44px minimum targets (64px on the kiosk), labels on every control, alt text on product images, `aria-live` regions kept where the scripts already update messages, contrast AA. Copy is plain and professional: no emoji, no exclamation marks, no demo wording.
6. **Icons are inline SVG**: 20px, 1.5px stroke, square caps, `currentColor`, from one sprite `frontend/icons.svg` used as `<use href="icons.svg#name"/>` (needs the pages served over http, as with `python -m http.server`). No third-party brand logos. The wordmark is a typographic mark set in Newsreader with letter-spacing, a placeholder name until a real brand asset exists.

### Files

- `frontend/styles.css`: tokens, font imports, base type, app bar, buttons, inputs, tables, badges, panels, empty and loading states, utilities. Loaded by every page before its own `<style>`.
- `frontend/icons.svg`: the icon sprite.
- Pages keep every id, JavaScript class name, API call and WebSocket handler unchanged. Markup changes only where layout needs a wrapper, with the same ids kept.

### Page checklist

- [x] index.html (done, reviewed)
- [x] chat.html (done, reviewed)
- [x] whatsapp.html (done)
- [x] mobile.html (done)
- [x] kiosk.html (done)
- [x] store-dashboard.html (done)
- [x] agent-monitor.html (done)
- [x] post-purchase.html (done)

### Redesign log

- **Shared files written:** `frontend/styles.css` (tokens, base type, app bar, buttons with all states, badges, panels, form fields, table, skeleton and empty states, reduced-motion) and `frontend/icons.svg` (about 45 line icons: arrows, check, alert, shield, lock, cart, bag, search, user, heart, star, tag, card, truck, box, map-pin, phone, chat, desktop, store, layout-grid, activity, cpu, send, mic, volume and more).
- **index.html:** app bar (wordmark, system status, session id in mono); left-aligned title block with a facts list instead of a centered hero; the four business figures as a ruled row; the six journey steps as a numbered timeline on one rule (active step has a heavy top rule); the eight experiences as grouped rows (Customer channels, In store, Operations, After purchase) with an icon, title, description and one button each; footer with the platform line and tech stack. All ids, the `.step` / `data-step` / `.active` hooks, every `onclick` and the whole script block are unchanged. Emoji and glass/gradient styles removed. Responsive at 1100, 768 and 480.
- **Content notes:** the four figures (15%, ₹4.2K, 42%, <2s) are the original sample text, not measured results; replace them with real numbers before showing this as production data. The `<title>` still says "Van Heusen" as before.
- **chat.html:** shared app bar (wordmark, language selector moved in from its old floating position, id kept); two-column layout: conversation history sidebar (white, ruled rows, active row marked by a dark left bar) and the chat column with a header strip (assistant name, status dot and text), a centered message column (max 820px) and a sticky input bar. Store replies are white boxes with a 1px line, customer messages are solid ink; timestamps in mono. Quick-reply buttons, product cards (name in serif, price in mono, accent-bar reasoning note), the cart panel (quantity steppers, ruled total, stamped discount label), the agent-activity label and the typing indicator are all restyled. Mic and send buttons now use inline SVG icons. On screens under 900px the sidebar becomes a horizontal strip above the chat, and under 480px it hides the conversation strip (New chat stays). The script block is byte-for-byte the original from `<script>` to the end; every id (`chatMessages`, `messageInput`, `voiceBtn`, `sendBtn`, `languageSelect`, `statusText`, `conversationsList`) and every class the script creates (`message`, `message-bubble`, `suggestions`, `suggestion-btn`, `product-card`, `cart-display`, `agent-indicator`, `conversation-item`, `status-dot`) is kept.
- **Known limit:** the script itself builds some text with emoji (the agent-activity line, the cart heading, many scripted replies). Since JavaScript was off limits, those emoji remain in chat messages. Say if you want the strings cleaned up in a separate pass.

### Streaming replies and emoji cleanup (after chat.html)

- **Streaming:** new `POST /api/chat/stream` and `POST /api/chat/approve/stream` (server-sent events). Events: `progress` (agent started or finished, payment gateway tried, guard blocked the message), `token` (the next 3 words of the reply) and `done` (the same full reply object `/api/chat` returns). Code is in `ai_workflow/channels/stream.py` (`stream_reply`, `EventCollector`, `split_into_pieces`); the collector forwards every update to the real WebSocket manager as well, so the agent monitor still sees everything. `STREAM_PIECE_DELAY_SECONDS` (default 0.03, set to 0 in tests) paces the pieces. **Honest note:** the reply text is assembled by the server from agent results (templates), not written by an LLM, so it is complete the moment the agents finish; the streaming paces its delivery so the customer reads while it arrives. What really shortens the wait is the progress events (the customer sees which agent is working during a slow payment). If an LLM ever writes the reply, the same events carry real tokens with no client change.
- **chat.html:** English replies and payment approvals now use the streaming endpoints (`streamChatReply`, `readEventStream`, `startStreamingBotMessage` added to the script). Other languages still use `/api/chat` because the whole reply must be translated first. If streaming fails, the old smart-fallback replies still show. Nginx: `proxy_buffering off` added to the `/api/` block in AWS_DEPLOYMENT.md (the response also sends `X-Accel-Buffering: no`).
- **whatsapp.html** streams too (see its entry below).
- **Emoji cleanup:** removed from every string in the `chat.html` script (about 165 lines) and from the backend reply text in `orchestrator_graph.py` (20 lines). List markers became "- " or numbers, the status marks are plain words. One line was left on purpose: the regex in `chat.html` that strips emoji before text is spoken aloud. Tests that match reply text (`Hello!`, `Order confirmed`, `cancelled`) still hold. Emoji remain in `whatsapp.html`, `mobile.html`, `kiosk.html`, `store-dashboard.html`, `post-purchase.html` and `agent-monitor.html` until each is redesigned (WhatsApp will keep a very small number on purpose).
- **Tests added (59 total):** reply splitting rejoins exactly, stream order is progress then text then done, and the stream endpoint returns `text/event-stream`.

### whatsapp.html redesign

- **Look:** kept WhatsApp's own dark theme so it reads as WhatsApp (dark teal-black background with a faint cross pattern, panel-grey received bubbles, dark-green sent bubbles with small tails, green accents, a pill input and a round send button). It is now a full-height column (max 480px, centered on wide screens) instead of a floating rounded phone mockup with a shadow. Type is Instrument Sans; product names use Newsreader; badges use the mono font. Quick replies are 44px-high two-column buttons (one column on phones). Header has a circular avatar with an inline SVG, name, "Online" and the voice toggle. The shared app bar is not used on this page, as planned.
- **Why dark and not the ivory palette:** the script builds the cart with inline dark colours and even finds old cart panels by the style text `background: #1f2c34`, so a light theme would have needed script changes.
- **Fixed without touching the script logic:** the script looks up an element called `chat` (which did not exist) when it refreshes the cart after an item is removed, so that refresh threw an error. The chat area now sits inside a wrapper with `id="chat"`, so it works. Plain-text bubbles now keep line breaks (`white-space: pre-line`); the cart bubble is excluded so its markup does not gain extra gaps.
- **Streaming:** `askBackend` and `answerApproval` now use `/api/chat/stream` and `/api/chat/approve/stream`; the reply grows in the bubble as words arrive, the typing dots show until the first words, the approval buttons and cart sync run when the stream ends. `readEventStream` and `showBackendReply` (rewritten) are in the script.
- **Emoji:** cleaned from the script (76 lines). Kept on purpose: the waving hand in the greeting, and the emoji list inside the speech filter regex. The cart heading is now "Your Cart (N items)" and the cart-refresh check looks for the word "Cart" instead of the emoji plus word, so both stay consistent.
- Ids kept: `chatContainer`, `messageInput`, `voiceBtn`, `ttsToggle`; classes the script creates: `message`, `message-bubble`, `product-card`, `quick-reply`, `typing-indicator`; hooks `.enabled` and `.listening`.

### mobile.html redesign

- Removed the fake phone frame, fake status bar and floating pills. Now a real mobile storefront: sticky white header (Van Heusen name, the clock label the script updates, a "Liked N" counter), a short intro ("Step 1 of 6 / Browse and like"), an image-led product grid (2 columns on phones, 3 from 768px) with fixed 4:5 images, name in serif, price in mono, an outlined stamp badge, and a square heart button; plus a sticky bottom action bar with "Scan in Store" and "Continue on WhatsApp".
- The script writes text into the like button, so the heart is drawn with a CSS background image (outline, and filled when `.liked`); the button text strings in the script are now empty. The counter text became "Liked N". Template edits inside the script: the like button got an `aria-label`, the image-error emoji became an SVG icon. Emoji removed from the script's strings, logs and alert.
- Kept: ids `productGrid`, `likeCount`, `currentTime`, `like-<id>`; classes `liked`, `floating-cart`, `floating-kiosk` (now on buttons); every `onclick`, API call and storage key.

### kiosk.html redesign

- Replaced the card floating on a dark gradient with a full-screen touch layout: dark ink header (title, store name and kiosk id in the corner), a scrolling content area, and a help footer. Base type 20px, every button 72px or taller.
- Landing: left copy (56px headline, one primary scan button) and a square viewfinder with a scan icon and a plain red scan line (no glow). Recognised-customer screen: a heavy top rule and a 44px welcome line instead of a gradient banner; cart and liked items as ruled rows with mono prices and an outlined quantity stamp; four large action buttons in a 2-column grid (1 column under 900px) with inline SVG icons; "Complete Purchase" is the solid one. Payment terminal: dark ink display with a 72px mono amount, three large payment tiles (now real buttons), and an outlined green success panel with a check icon.
- Kept: all ids (`landingScreen`, `sessionScreen`, `posScreen`, `scanLaser`, `welcomeMessage`, `contextSummary`, `cartSection`, `likedSection`, `kioskCartItems`, `kioskLikedItems`, `posAmount`, `paymentMethods`, `processing`, `storeName`, `kioskDetails`), the `.active` toggles, the `.cart-item` / `.liked-item` / `.quantity-badge` / `.price` classes the script renders, and every `onclick`, API call and alert. Emoji removed from the script strings and alert texts.

### store-dashboard.html redesign

- Light, dense dashboard on the shared app bar (wordmark, "Store dashboard" tag, Refresh Cart button). Page title block, then one ruled panel: customer row (square photo with click-to-enlarge, name in serif, phone and location with icons, a gold-member stamp) above a 3-column grid (Recent Online Activity | Cart Contents | AI Recommendations) separated by hairlines; the kiosk notification alert sits full width on top of the grid when it appears. 14px text, mono section labels, ruled rows instead of cards, square quantity buttons, a ruled totals block, and the two actions at the bottom right (Apply Bundle Offer outlined, Process Checkout solid). Responsive: 2 columns under 1100px, 1 under 768px.
- The script builds rows with inline colours made for the old dark theme; those colour values were retuned inside the strings to the palette (`rgba(255,255,255,0.5-0.8)` to `var(--ink-soft)`, `#667eea` to `var(--ink)`, `#38ef7d` to `var(--success)`, `#ff4757` toast to `var(--danger)`, the gold upsell tint to `var(--stone)` / `var(--accent)`). Logic, ids (`recentActivityContainer`, `notificationsSection`, `kioskNotifications`, `dashboardCartItems`, `dashboardCartTotals`, `imageModal`, `modalImage`) and classes the script renders (`activity-item`, `product-item`, `cart-controls`, `cart-qty-btn`, `cart-qty`, `cart-remove`, `notification-item`, `notification-actions`, `acknowledge`, `dismiss`) are unchanged. Emoji removed from the script strings.

### agent-monitor.html redesign

- Dark engineering console (the only dark page): top bar with the wordmark and "Agent monitor" tag, a four-figure metrics strip (Connection, Session, Active Agents, Total Calls), a scenario toolbar with outlined mono buttons (Injection Attack in red), an approval panel with a decision-coloured left bar, seven agent tiles with status stamps (idle, processing, success, failed) and call counts, and the event log as ruled mono lines with a coloured left bar per agent. Script unchanged except that the SUCCESS/FAILED word replaced the check and cross emoji in payment log lines, and emoji were removed from log strings. All ids and the `status-*`, `log-*`, `active`/`success`/`failed`, `show` hooks are kept.

### post-purchase.html redesign

- Roomy single reading column (max 760px) on the shared app bar ("Order follow-up", "Step 6 of 6"). Large serif headline "Thank You, Rahul!" under a double rule; the order timeline is a vertical stepper with square icon tiles (completed in green, pending in gold) joined by a hairline, each step with a title, a serif italic quote block for the WhatsApp message, and a mono timestamp. Rating card with five square star buttons (filled in gold when selected) and a 2x2 grid of outlined actions with SVG icons; recommendations as ruled rows with a solid Add button and an outlined offer note; a loyalty footer with the points figure in mono and a Back to Dashboard button.
- Template edits inside the script: the timeline emoji became SVG icons (check-circle, box, truck, gift), the gold gradient offer banner became a `special-offer` class, and the grey inline text colour was dropped. The star spans became buttons carrying the same `star` class and `data-rating`, so the rating handler works unchanged. Ids `timelineContainer`, `recommendationsSection`, `ratingFeedback`, `pointsEarned` and the `active` hook are kept; every `onclick`, API call and alert is unchanged (emoji removed from their text).

### Redesign wrap-up

- Shared: `frontend/styles.css`, `frontend/icons.svg`, `frontend/config.js`. No gradients, shadows, blur, purple or emoji icons remain in the page styles; the three places emoji remain are the speech-filter regexes in chat and WhatsApp and the waving hand in the WhatsApp greeting.
- Checked by reading only (nothing was opened or run): every `getElementById` id used by each script exists in its page (the one exception, `typing`, is created by the script), and every page loads `styles.css` and `config.js`.
- Not covered: the pages were not viewed in a browser, so spacing, line wraps and small-screen behavior need an eyeball pass. The four sample figures on the home page are still placeholders. The fonts come from Google Fonts.

### Startup warm-up

- **Why:** the first customer should not pay for one-time work. Before this, the catalog files were read on the first request, the Postgres pool did not wait for its connections, the first model call opened the network connection to Claude/OpenAI, and the translation library was imported on the first translate request.
- **What runs at startup (`ai_workflow/warmup.py`, called from the lifespan after the graph is built):** `catalog_store.preload()` reads the three data files (and fails startup if one is missing); `googletrans` is imported in a thread; and, when `WARMUP_LLM` is true (default), one tiny request is sent to the supervisor model and the recommendation agent's model in a background task, so the app can already serve while they warm. A failed warm-up call only logs a warning.
- **Postgres:** `open_postgres` now opens the pool with `wait=True` (10 second limit), so the minimum connections are ready before the first request and a database that is down fails inside the startup retry loop instead of at the first customer.
- **Already warm before this change:** imports, the compiled graph, the six agents and the compiled guardrail patterns (all at import), and the Redis connection (the startup ping).
- **Cannot be warmed:** the model's own response time, the simulated payment gateway delays (about 2.7 seconds by design), and fonts on the customer's first page visit. With several uvicorn workers each worker warms itself.
- **Not done:** a dry run of the whole graph at startup (it would call the model again and would need a throwaway checkpoint store).
- **Setting:** `WARMUP_LLM` in `.env.example`. **Tests added (62 total):** preload counts, no-model warm-up, and a failing model not stopping startup.

### Fix: duplicate metrics on startup (Windows reload mode)

- `uv run python main.py` crashed with `DuplicateTimeseries` because uvicorn's reload child process on Windows imports `main.py` twice (as the script and as `main`), and the two Prometheus metrics were created in `main.py`. They now live in `ai_workflow/metrics.py`, which Python loads once. The yellow "Variable not allowed in type expression" note seen inside `prometheus_client/metrics.py` is a type-checker warning in the library, not an error in this project.

### whatsapp.html: guided flow (follow-up questions, dead button, rating)

- **Problem found:** after showing products or a store check, the page showed the result and went quiet, with no question about what to do next. The "Add to Cart" button offered after a store check sent the action `add_this`, which the page never handled, so it did nothing.
- **Fixes (script edits in `whatsapp.html`):** after the liked products and after the matching items the page now asks what to do next and offers buttons (Check in store, Matching accessories, Add the tie/belt, View cart, Checkout). After a store check it asks "reserve it for a try-on, or add it to your cart?" with Reserve Now, Add to Cart, Other stores and Checkout. After a reservation it asks if there is anything else and adds a Checkout button. New actions: `add_this` (adds the product last checked, remembered through `shownProducts` and `lastCheckedProductId`), `view_cart`, `track_order`.
- **Rating:** the streamed reply to a confirmed payment now carries `order_id` (backend: `_reply` in `channels/base.py` returns `order_id` when the payment succeeded). The page then asks "How was your shopping experience?" with 1 to 5 buttons and posts the answer to `/api/feedback/rating` with that order id, then thanks the customer and offers Browse more / Track my order. Test updated: the paid-order test also checks `reply["order_id"]`.
- **Still scripted:** the product, store and stock details in this page's own replies are fixed demo text; only payment, offers, returns, delivery and anything unrecognised go to the real backend.

### Dead-end audit (all customer channels)

Checked every path a customer can take in each channel for a point where nothing tells them what to do next, or where the page says something untrue.

| Channel | Found | Fixed |
|---|---|---|
| **Kiosk** | Worst one: after "Complete Purchase" it always showed "Payment Successful" and redirected, ignoring what the backend answered (a declined payment, an empty server cart, a failed order save all looked like success). The success message also appeared before any payment happened. | New states: "Processing payment..." then either success, or "Payment not completed" with the reason and the payment methods shown again to retry. The kiosk first copies its local cart to the backend (`syncKioskCartToBackend`) so the server can price it. Redirect only happens after payment and order both succeed. Back to Cart resets all three panels. |
| **WhatsApp** | A debug line ("Debug: Cart has 0 items. Did you add items in this session?") was shown to customers on an empty cart; "Your cart is now empty" after removing the last item had no buttons; the Call Powai store reply and the coupon reply had no buttons; backend replies (discount, delivery, return, blocked, cancelled payment) ended with no next step; a backend error offered nothing. | Debug line removed; buttons added to each of those; every backend reply now ends with cart-aware next steps (View cart / Checkout / Browse, or Browse / Recommendations); errors offer "Try again" (`retry_backend` re-sends the last request). Earlier fix: follow-up questions, the dead Add to Cart button and the rating prompt. |
| **Web chat** | Suggestion buttons were only offered for a few keyword cases or in the first two messages, so most backend replies ended with none; after approving a payment there was nothing; no rating prompt; removing a cart item or opening an empty cart left no next step; suggestions like "Check my cart" went to the backend, which has no cart answer. | `addNextStepSuggestions` after every backend reply that had no specific suggestions, after a payment decision and after cart changes; a rating prompt (1 to 5, saved through `/api/feedback/rating`) after a confirmed order; cart questions ("view my cart") are answered locally from the shared cart before calling the backend. |
| **Mobile** | No dead end: the bottom bar is always visible, and Continue on WhatsApp with no likes explains what to do (an alert). | None needed. |
| **Store dashboard** | Empty cart and no activity show a plain message; staff actions explain themselves with an alert when the cart is empty. | None needed. |
| **Post-purchase** | Rating, support, tracking, invoice and returns all end in an alert or a message, and Back to Dashboard is always shown. | None needed. |
| **Agent monitor, home page** | Errors are written to the log; the home page falls back to a demo session when the backend is down. | None needed. |

- Not changed: the backend's own replies. A cleaner design would be for the backend to return a `next_steps` list so every channel shows the same buttons; the pages use their own cart-aware defaults for now.
- All of this is edited by reading only; none of it has been run.

### Starting fresh (reset between runs)

- **Where state lives:** the browser (localStorage: session id and token, cart, likes, chat history, current step), Redis (the live session, cart and likes, plus a pointer from the customer to their latest session) and Postgres (orders, ratings and checkpoints). A new session copies the cart, likes and history of the customer's latest session, so a new browser alone does not give an empty start.
- **One click:** the home page has a "Start fresh" button. It clears the browser storage and creates a session with `POST /api/session/create?customer_id=CUST001&fresh=true`, which starts with an empty cart and no likes (`create_session(..., carry_over=False)`). Orders and ratings already saved in Postgres are kept. Other pages should be reopened from the home page afterwards so they pick up the new session.
- **Manual options:** browser console `localStorage.clear()` (or DevTools > Application > Local Storage > Clear for localhost:3000); `docker compose exec redis redis-cli FLUSHALL` for Redis; `docker compose down -v` then `docker compose up -d` to wipe Redis and Postgres together.
- **Tests added (64 total):** a fresh session has no inherited cart or likes, and the API's `fresh=true` option.

### Fix: product ids that did not match the catalog

- **Bug:** the mobile page's Striped Tie is `VH005B`, but WhatsApp's lists called it `VH005` (the greeting printed "undefined" and the tie was dropped) and the backend had no `VH005B`.
- **Fixed:** `VH005B` (Striped Silk Tie) added to `data/products.json`; WhatsApp and kiosk use it. Kiosk and post-purchase product lists now use real catalog ids and names (they had made-up ones such as a wallet, cufflinks, charcoal blazer). Store dashboard belt is `VH006`. Chat accessory and new-arrival lists use catalog ids. The two blazers chat suggests (`VH010` Black, `VH011` Navy) were added to the catalog (made-up stock). Catalog now has 32 products.
- **Rule going forward:** any id a page sends to the backend must exist in `data/products.json`.

### Fix: stray `**` in replies

- The reply templates in `ai_workflow/graph/orchestrator_graph.py` used markdown bold (`**text**`). WhatsApp shows plain text, so the asterisks were visible. Removed all five (product names, loyalty points, special offer, order confirmed, delivery). `chat.html` turns `**bold**` into real bold itself, so its own scripted replies are unchanged. Rule: backend replies are plain text.

### Fix: whatsapp store check shows every store

- "Check in Store" on a product card, the "Check in store" / "Other stores" buttons and typed store questions used fixed demo text (one store, "3 pieces in stock"). They now call `POST /api/store/check` (new `showStoreStock` in `whatsapp.html`) and list every nearby store with its real stock for that product, then offer "Reserve at <store>" buttons for stores that have it (up to 3), Add to Cart and Checkout. If no store has it, it says so and offers similar items. Reserving calls `POST /api/store/reserve` (`reserveAtStore`) and only confirms if the backend accepted it. Errors offer "Try again". The old fixed `reserve_bandra` / `reserve_powai` / `notify_andheri` replies remain for the other flows that still use them.

### Fix: two different totals in WhatsApp

- **Bug:** after adding items the page quoted ₹3,060 (its own sum: 10% off), but the approval question said ₹2,720 (the backend's price: 10% multi-buy off and 10% loyalty points). The page also gave 10% off for a single item and counted discounts by quantity while the backend counts cart lines.
- **Fix:** the backend is the only place that prices a cart. `GET /api/cart/{id}` now also returns `pricing` (offers, discount, `points_used`, `final_price`, from `loyalty_discount`). `whatsapp.html` no longer works out discounts itself: it adds or removes the item on the backend first, reloads `pricing` (`refreshPricing`), and shows the backend's total in "Added to cart", the cart message (new "Loyalty points" row) and quantity changes. Test added (65 total).
- **Not changed:** other pages (chat, kiosk, store dashboard, post-purchase) still have their own local discount sums and can show a different total from the backend; same fix applies if you want them aligned.

### Fix: every page shows the backend's price

- **Shared helpers in `frontend/config.js`:** `cartPricing`, `refreshPricing()`, `payableTotal(fallback)`, `offerBadgeText()`. They read `pricing` from `GET /api/cart/{id}` (offers, discount, `points_used`, `final_price`). `whatsapp.html` now uses these shared copies instead of its own.
- **chat.html:** cart view, "Added to cart" message and quantity changes add or update the backend first, then show its total and offer badge. The typed "card/upi" shortcut saves the backend total as `orderTotal`.
- **kiosk.html:** `showPOSPayment` syncs the cart, asks the backend for the price and shows it on the terminal; after a successful payment the charged amount (`payment.amount`, now returned by `/api/payment/process`) is saved as `orderTotal`.
- **store-dashboard.html:** cart totals show offer, loyalty points and total from the backend (`showBackendTotals`); checkout uses it. The bundle-offer dialog no longer promises computed savings; after the belt is added it shows the real new total.
- **post-purchase.html:** the invoice total is the amount actually charged (`orderTotal`); the discount line is the difference ("Offers and loyalty points").
- **Tests:** payment test also checks the returned `amount` (65 tests, none run). Every page's script, together with `config.js`, passes a Node syntax check.
- **Still local marketing text, not prices:** chat's scripted sales replies (for example "20% bundle discount unlocked", "bundle price" suggestions) and the home-page sample figures are fixed wording. The dashboard's upsell box also says "20% bundle discount" as a promise, which matches the backend rule for 3 or more cart lines.

### Web chat: product cards with photos

- `addProductCard` in `chat.html` (used by every recommendation, accessory and outfit list) now shows a 4:5 photo above the name. `config.js` has `PRODUCT_IMAGES` (catalog id to file in `frontend/images`) and `productImage(id)`. Only six photos exist (VH001, VH002, VH003, VH004, VH005B, VH006); every other product, and any photo that fails to load, shows a plain stone-coloured placeholder with a garment outline. Adding a photo later is one line in `PRODUCT_IMAGES`.

### Home page: product, not building blocks

- Removed from `index.html`: the "Powered by LangChain + LangGraph" line, the footer tech-stack line (FastAPI, LangChain, LangGraph, Claude AI), and the four business figures (15%, ₹4.2K, 42%, <2s) with their styles. Web chat's welcome text no longer says "powered by Claude". The agent monitor still names its agents (it is the engineering view). The tech stack stays in the README and docs.

### Fix: dashboard cart and WhatsApp reservations

- **Dashboard cart empty:** `store-dashboard.html` read the cart only from browser storage, so it could show "Cart is empty" while the backend (and WhatsApp) had items. `loadFromBackend` now reads `GET /api/cart/{id}` and `GET /api/session/{id}` every 2 seconds (browser storage is only a fallback when the backend is down), updates the cart, totals and price.
- **WhatsApp reservation not visible:** a kiosk reservation wrote a browser-storage notification the dashboard displayed; a WhatsApp reservation only saved `reserved_store` on the backend and nothing read it. Now the dashboard shows an "Items Reserved For Pickup" notice and the store name from `session.reserved_store`, and the kiosk reads it too (store name and details in the header, "Your items are reserved for you at ..." in the welcome text, and the order is saved at that store instead of always Bandra). The kiosk knows all four stores (it only knew two). The fixed `reserve_bandra` / `reserve_powai` buttons in WhatsApp now call the real reserve endpoint too (they only printed text before).

### Fix: one store everywhere (reserved at Powai, packed at Bandra)

- **Bug:** after reserving at Powai on WhatsApp, "Track my order" said "packed at Bandra Store" (fixed text), and the post-purchase timeline said the same. The web chat's store buttons only changed browser storage and the kiosk URL, never the backend.
- **Fix:** the backend's `session.reserved_store` is the single answer to "which store". WhatsApp track order and the post-purchase "Order Packed" step read it (`our store` if none is reserved). In `chat.html`, choosing or reserving Bandra or Powai now calls `/api/store/reserve` (`reserveStoreOnBackend`) before opening the kiosk. The order saved in Postgres already used `reserved_store` as its store. Kiosk and dashboard already read it (see the previous fix).
- **Still fixed text in chat.html:** the directions and contact replies for Bandra, and the Bandra-only store lists in the chat's scripted replies.

### Store associate alerts: reservation and pickup

- **What:** like the kiosk's try-on request, a WhatsApp reservation now alerts the associate, who accepts or rejects it, and a paid order tells the associate the customer will come to pick it up. Stored on the session as `store_alert` (`kind` reservation or pickup, store, items, order id and total for pickups, `status` pending, accepted or rejected), so it works across channels.
- **Backend:** `POST /api/store/reserve` creates the reservation alert; `create_order` (`tools/orders.py::tell_store_about_pickup`) replaces it with a pickup alert when the order has a store (the reserved store, or the kiosk's store); new `POST /api/store/alert/respond?session_id=&action=accept|reject` records the answer, clears `reserved_store` when a reservation is rejected, and sends a `store_alert_response` WebSocket event. 4 tests added (69 total).
- **Dashboard:** `store-dashboard.html` shows "Items Reserved For Pickup" (Accept, Cannot Hold) or "Paid Order To Hand Over" (Will Have It Ready, Cannot Hold) inside Kiosk Notifications, refreshed every 2 seconds.
- **WhatsApp:** after reserving, the customer is told the store was asked and `watchStoreAlert` reports the answer (confirmed, or cannot hold with an "Other stores" button). After payment `announcePickup` says the store was told they will collect, and reports the answer the same way. The watcher stops after about 2 minutes.
- **Not done:** the web chat does not wait for the answer, and the kiosk's try-on notification still uses browser storage (it works only on one browser).

### Cart messages explain the price

- **Problem:** with one item the page said "Total: ₹2,520" under an item priced ₹2,800. The ₹280 was loyalty points taken automatically (10% cap), but nothing said so, and the offer for 2 items was never announced.
- **Fix:** "Added to cart" (WhatsApp and web chat) now shows items, subtotal, the offer line (only when there is one), the loyalty points line (when used) and "Total to pay" (`cartSummaryText` in `config.js`). The moment the cart earns an offer it says so once ("Multi-buy: 10% off on 2+ items has been applied to your cart", `newOfferText`). The backend's `pricing` now carries `next_offer` (items needed, percent) from the same rules, and the page says "Add 1 more item to get 20% off your cart" (`nextOfferText`) instead of fixed text. Test added (70 total, none run).
- **Rules unchanged:** offers count cart lines (2 lines 10%, 3 or more 20%); loyalty points apply automatically up to 10% of the item subtotal.

### Loyalty points are the customer's choice

- **Before:** points (1 point = ₹1, at most 10% of the item subtotal) were taken off every cart automatically, so one ₹2,800 shirt cost ₹2,520 with no explanation.
- **Now:** `loyalty_discount(customer_id, cart, use_points=False)` only subtracts points when the customer chose to. The result also reports `points_usable` (what they could use) and `use_points`. The choice is `session["use_points"]` (default false, reset after an order, not copied to a fresh session); `POST /api/cart/points?session_id=&use=true|false` sets it and returns the new price. The price shown on every page, the approval question, the payment and the invoice all read it (`state["use_points"]` for the graph).
- **Pages:** the "Added to cart" message shows "Loyalty points you can use: ₹X" and offers **Use my loyalty points** (a button on WhatsApp, a suggestion in the web chat; typing "use my loyalty points" in the chat also works). Choosing it shows the new breakdown. Offers (2 lines 10%, 3 or more 20%) are unchanged.
- **Tests:** existing expectations changed to the no-points price (one shirt ₹2,500, shirt plus tie ₹3,060 and so on); new tests for the choice and the points route (71 total, none run).
- **Take points off again:** WhatsApp shows **Keep my points** after points are applied (and **Use my loyalty points** after); the web chat has the matching suggestions, and typing "keep my loyalty points" works. Both call `POST /api/cart/points?use=false`.
- **Zero row hidden:** the dashboard cart and the WhatsApp cart message show the "Loyalty points" row only when points are used.

### Fix: checkout failed after the points change

- `use_points` was added to `create_initial_state` and read by the approval step, but not declared in the `AgentState` TypedDict, so LangGraph dropped it and `ask_for_approval` raised a KeyError; every checkout answered with the generic "I'm having trouble" reply. Declared it in `ai_workflow/graph/state.py`. Rule: any new key put in the graph state must also be listed in `AgentState`. The existing graph tests (checkout pauses for approval) cover this path.

### WhatsApp: Reserve for try-on button

- New **Reserve for try-on** button (action `reserve_try_on`) next to Checkout, Keep my points and Show Ties & Belts after points are applied, and on the "Added to cart" and "Keep my points" replies. It runs the real store check for the first item in the cart (`showStoreStock`, now with a label), lists every store with stock and offers Reserve at (store) buttons; the reservation alerts the store associate as described above. With an empty cart it asks the customer to add something first.

### Fix: the White Premium Shirt was sold out everywhere

- `VH002` (White Premium Shirt, on the mobile page and in WhatsApp) had been set to zero stock in every store on purpose, to demo the out-of-stock path. It confused the main journey (store check and try-on reservation showed nothing available), so it now has stock (4 Bandra, 3 Powai, 2 Andheri, 2 Kurla in every size). The sold-out demo product is now `VH001B` (Light Blue Formal Shirt), which is not on the mobile page; the inventory test uses it.
- **Still open:** the product cards say "Available" even for a sold-out product, and a sold-out product can still be added to the cart. Say if you want those checked.

### Out of stock: cards and cart

- **Cards:** `GET /api/products/availability` says which products have stock in any store (`catalog_store.is_in_stock`). WhatsApp and web chat load it once (`loadAvailability` in `config.js`) and a sold-out product card says "Out of stock" with no Add to Cart (WhatsApp offers "Similar items", the web chat shows a disabled button).
- **Cart:** `POST /api/cart/add` returns 409 with a message and in-stock alternatives when the product is sold out in every nearby store for that size (the cart is unchanged). WhatsApp and the web chat undo their local copy (`undoLocalAdd`), say so, and show up to 3 similar in-stock items. The store check's alternatives now only list in-stock products.
- **Tests:** 2 added (73 total, none run). **Kiosk and mobile:** the kiosk's "add liked items to cart" now asks the backend first (one call per item), skips a sold-out item and lists it in the confirmation ("Out of stock, not added"); the mobile product grid shows an "Out of stock" label and a faded photo for sold-out products (still likeable).

### README rewritten (asked for by the user, so the earlier "do not edit README.md" rule no longer applies to this one change)

- Kept every claim and metric (EY Techathon Top 61 of 185,000+, ~1.6 s cart update, under 100 ms sessions, 1–3 s replies, 7 languages, 3 gateways, 6 agents). Updated: test count (45 to 73), new features (honest server-side pricing, opt-in loyalty points, store associate alerts, in-stock checks, streaming replies, OpenAI fallback, evals), a "Built for production" table, `uv`/Docker quick start, new project structure, a link to `video/agentic_ai_video.mp4`.
- Removed: "live AWS deployment", the AWS badge, "Runs on AWS EC2". The Deployment section now says the project is not deployed yet but is ready to be (`DEPLOYMENT.md`, `AWS_DEPLOYMENT.md`).
- The test count (73) and the guardrail, price and alert claims describe code that has been written but not run; run `uv run pytest` before relying on the count.

### README: demo video preview

- Made with ffmpeg from `video/agentic_ai_video.mp4` (3 min 44 s, 1080p, 40 MB): `video/demo_preview.gif` (the whole walkthrough at 10x speed, 22 s, 1.6 MB, plays by itself in the README) and `video/demo_preview.jpg` (a still). The README shows the GIF as a clickable image that opens the full video, plus a text link.
- GitHub does not play a repo `.mp4` inside the README. For a real inline player, edit README.md on github.com and drag the mp4 into the editor (limit 100 MB); GitHub inserts a `user-attachments` link on its own line, which shows a player. Alternative: upload to YouTube (unlisted) and link the thumbnail.

### .gitignore

- Rewritten. Ignores secrets (`.env` and `.env.*`, but `.env.example` stays committed), virtual environments, Python caches, test and lint output, `evals/results/`, `data/sessions.json`, logs, local database files, editor and OS files, and `.claude/settings.local.json`. Deliberately committed: `uv.lock` (so installs repeat exactly), `CLAUDE.md`, `.dockerignore`, `.github/`, and `video/` (the demo).

### README: performance table restored

- The rewrite kept the numbers that were in the last committed README but not the longer "Performance" table from earlier commits (7ad3758 and before). Restored it as a "Performance" section: session creation under 100 ms, product like under 50 ms, agent orchestration 0.5-2 s, AI chat 1-3 s, order modification about 1.6 s, payment with failover about 2.7 s worst case, WebSocket updates under 50 ms; the 2.7 s figure is also back in the payment failover feature line. These are the figures from the earlier README, not new measurements.

### README: evaluation results added

- Added an "Evaluation" section and a features line with the figures from the user's resume: 98% routing accuracy over 300+ turns, 96% task completion on 50 multi-turn conversations, 98% prompt-injection defence. These were supplied by the user. They have not been produced by the evals in this repository (never run), so the section tells readers to re-run `uv run python -m evals.run_evals`. If a re-run gives different scores, change the README and the resume to the real ones.
