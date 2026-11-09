"""Shared test setup: fake Redis, no LLM, instant payment gateways, in-memory checkpoints."""

from pathlib import Path

import fakeredis
import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from ai_workflow.agents import AGENTS
from ai_workflow.graph import supervisor
from ai_workflow.graph.orchestrator_graph import create_orchestrator_graph
from ai_workflow.graph.state import create_initial_state
from ai_workflow.integrations.payments.gateways import GATEWAYS, PayU, Razorpay, UpiDirect
from ai_workflow.settings import settings
from ai_workflow.storage import redis_store
from main import app

ROOT = Path(__file__).resolve().parents[1]


class FakeManager:
    """Stands in for the WebSocket manager and records every message."""

    def __init__(self):
        self.sent = []

    async def send_agent_update(self, session_id, message):
        self.sent.append(message)

    @property
    def types(self):
        return [message["type"] for message in self.sent]


@pytest.fixture(autouse=True)
def test_setup(monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", str(ROOT / "data"))
    monkeypatch.setattr(settings, "GUARDRAILS_ENABLED", True)
    monkeypatch.setattr(settings, "STREAM_PIECE_DELAY_SECONDS", 0)
    monkeypatch.setattr(settings, "PAYMENT_GATEWAY_ORDER", ["Razorpay", "PayU", "UPI Direct"])
    monkeypatch.setattr(settings, "PAYMENT_GATEWAY_TIMEOUT_SECONDS", 5)

    # No LLM calls: the supervisor uses keyword rules and agents use template text
    monkeypatch.setattr(supervisor, "llm", None)
    for agent in AGENTS.values():
        monkeypatch.setattr(agent, "llm", None)

    # Demo behavior (Razorpay times out, PayU is declined, UPI works) without the waiting
    monkeypatch.setitem(GATEWAYS, "Razorpay", Razorpay(delay_seconds=0))
    monkeypatch.setitem(GATEWAYS, "PayU", PayU(delay_seconds=0))
    monkeypatch.setitem(GATEWAYS, "UPI Direct", UpiDirect(delay_seconds=0))

    monkeypatch.setattr(redis_store, "_client", fakeredis.FakeRedis(decode_responses=True))


@pytest.fixture
def graph():
    return create_orchestrator_graph(InMemorySaver())


@pytest.fixture
def manager():
    return FakeManager()


@pytest.fixture
def session_id():
    return redis_store.create_session("CUST001")


@pytest.fixture
def make_state():
    def make(text, cart=None, liked_products=None):
        return create_initial_state(
            "SESSION_test", "CUST001", "web", text, cart=cart, liked_products=liked_products
        )
    return make


@pytest.fixture
def run_graph(graph, make_state):
    async def run(text, cart=None):
        return await graph.ainvoke(
            make_state(text, cart), config={"configurable": {"thread_id": "SESSION_test"}}
        )
    return run


@pytest.fixture
def client(graph):
    app.state.graph = graph
    return TestClient(app)
