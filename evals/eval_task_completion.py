"""Task completion: 50 multi-turn conversations, each passes when its success_check holds at the end.

Each conversation may start with a cart (product ids). When a payment is paused for approval,
the conversation's `approve` value is the answer.
"""

import asyncio
from typing import Any, Dict, List

from evals.common import build_graph, build_report, load_goldens, make_cart, send_message

NAME = "task_completion"
GOLDEN_FILE = "conversation_goldens.json"
MAX_PARALLEL_CONVERSATIONS = 5

# Each check gets the graph result of every turn in the conversation.
SUCCESS_CHECKS = {
    "order_saved": lambda results: any((r["payment_status"] or {}).get("order_id") for r in results),
    "cart_kept": lambda results: bool(results[-1]["cart"])
    and not any((r["payment_status"] or {}).get("success") for r in results),
    "payment_cancelled": lambda results: any("cancelled" in r["response"] for r in results),
    "stock_answered": lambda results: any("available" in (r["inventory_status"] or {}) for r in results),
    "return_policy_given": lambda results: any((r["support_info"] or {}).get("return_window") for r in results),
    "exchange_info_given": lambda results: any((r["support_info"] or {}).get("exchange_options") for r in results),
    "recommendations_given": lambda results: any(r["recommendations"] for r in results),
    "delivery_answered": lambda results: any((r["fulfillment_info"] or {}).get("status") == "available" for r in results),
    "discount_applied": lambda results: any((r["loyalty_info"] or {}).get("discount_amount", 0) > 0 for r in results),
}


async def play(graph, conversation: Dict[str, Any]) -> List[Dict[str, Any]]:
    thread_id = f"eval_{conversation['id']}"
    cart = make_cart(conversation.get("cart", []))
    results = []
    for text in conversation["turns"]:
        results.append(await send_message(graph, thread_id, text, cart, conversation["approve"]))
    return results


async def run_eval() -> Dict[str, Any]:
    conversations = load_goldens(GOLDEN_FILE)
    graph = build_graph()
    limit = asyncio.Semaphore(MAX_PARALLEL_CONVERSATIONS)

    async def check(conversation):
        async with limit:
            try:
                results = await play(graph, conversation)
            except Exception as error:
                return {"id": conversation["id"], "goal": conversation["goal"], "error": str(error)}
        if SUCCESS_CHECKS[conversation["success_check"]](results):
            return None
        return {
            "id": conversation["id"],
            "goal": conversation["goal"],
            "success_check": conversation["success_check"],
            "last_response": results[-1]["response"],
        }

    outcomes = await asyncio.gather(*(check(conversation) for conversation in conversations))
    failures = [outcome for outcome in outcomes if outcome]
    return build_report(NAME, len(conversations), failures)
