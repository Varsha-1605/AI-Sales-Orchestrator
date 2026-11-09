"""Helpers shared by the evals. Run the evals from the repo root so DATA_DIR resolves."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from ai_workflow.graph.orchestrator_graph import create_orchestrator_graph
from ai_workflow.graph.state import create_initial_state

ROOT = Path(__file__).resolve().parents[1]
GOLDENS_DIR = ROOT / "goldens"
RESULTS_DIR = ROOT / "evals" / "results"


def load_goldens(file_name: str) -> Any:
    return json.loads((GOLDENS_DIR / file_name).read_text(encoding="utf-8"))


def build_graph():
    return create_orchestrator_graph(InMemorySaver())


def make_cart(product_ids: List[str]) -> List[Dict[str, Any]]:
    return [{"product_id": product_id, "quantity": 1, "size": "40"} for product_id in product_ids]


async def send_message(
    graph, thread_id: str, text: str, cart: Optional[List[Dict[str, Any]]] = None, approve: bool = False
) -> Dict[str, Any]:
    """Run one message through the graph. If it pauses for approval, answer with `approve`."""
    config = {"configurable": {"thread_id": thread_id}}
    state = create_initial_state(thread_id, "CUST001", "web", text, cart=cart)
    result = await graph.ainvoke(state, config=config)
    if result.get("__interrupt__"):
        result = await graph.ainvoke(Command(resume={"approved": approve}), config=config)
    return result


def build_report(name: str, total: int, failures: List[Dict[str, Any]], **extra: Any) -> Dict[str, Any]:
    passed = total - len(failures)
    report = {
        "name": name,
        "score": passed / total,
        "passed": passed,
        "total": total,
        "summary": f"{passed}/{total} passed ({passed / total:.1%})",
        "failures": failures,
    }
    report.update(extra)
    return report


def write_report(report: Dict[str, Any]) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{report['name']}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
