"""Runs every eval_*.py file in this folder, saves its report and prints a summary table.

Run from the repo root:  uv run python -m evals.run_evals
"""

import asyncio
import importlib
from pathlib import Path

from evals.common import write_report


async def run_all() -> None:
    rows = []
    for path in sorted(Path(__file__).parent.glob("eval_*.py")):
        module = importlib.import_module(f"evals.{path.stem}")
        report = await module.run_eval()
        write_report(report)
        rows.append((report["name"], report["summary"]))

    print(f"{'EVAL':<20} RESULT")
    for name, summary in rows:
        print(f"{name:<20} {summary}")


if __name__ == "__main__":
    asyncio.run(run_all())
