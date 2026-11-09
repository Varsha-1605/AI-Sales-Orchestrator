"""Routing accuracy: does the supervisor pick exactly the expected agents for each turn?

Expected agents are what a good router should return for the message, plus loyalty
whenever any agent runs. They are not copied from the keyword rules.
"""

import asyncio
from typing import Any, Dict

from ai_workflow.graph.state import create_initial_state
from ai_workflow.graph.supervisor import choose_agents
from evals.common import build_report, load_goldens, make_cart

NAME = "routing"
GOLDEN_FILE = "routing_goldens.json"
MAX_PARALLEL_CALLS = 10


async def run_eval() -> Dict[str, Any]:
    turns = load_goldens(GOLDEN_FILE)
    limit = asyncio.Semaphore(MAX_PARALLEL_CALLS)

    async def route(turn):
        cart = make_cart(["VH001"]) if turn["cart_has_items"] else None
        state = create_initial_state("eval_routing", "CUST001", "web", turn["message"], cart=cart)
        async with limit:
            return await choose_agents(state)

    actual_agents = await asyncio.gather(*(route(turn) for turn in turns))

    failures = [
        {"id": turn["id"], "message": turn["message"], "expected": turn["expected_agents"], "actual": actual}
        for turn, actual in zip(turns, actual_agents)
        if set(actual) != set(turn["expected_agents"])
    ]
    return build_report(NAME, len(turns), failures)
