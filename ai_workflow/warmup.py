"""Work done once at startup, so the first customer does not wait for it."""

import asyncio
import importlib

from loguru import logger

from ai_workflow.agents import AGENTS
from ai_workflow.graph import supervisor
from ai_workflow.settings import settings
from ai_workflow.storage import catalog_store

# Keeps a reference to background tasks so they are not garbage collected while running
_background_tasks: set = set()


async def warm_up_models() -> None:
    """Send one tiny request to each model in use, so the first real message does not pay for opening the network connection."""
    models = [model for model in (supervisor.llm, AGENTS["recommendation"].llm) if model]
    if not models:
        return
    results = await asyncio.gather(
        *(model.ainvoke([("user", "Reply with OK.")]) for model in models),
        return_exceptions=True,
    )
    failed = [result for result in results if isinstance(result, Exception)]
    for error in failed:
        logger.warning("Model warm-up failed (the first message will be slower): {}", error)
    logger.info("Models warmed: {} of {}", len(models) - len(failed), len(models))


async def warm_up() -> None:
    """Load the catalog, import the translation library and open the model connections."""
    counts = catalog_store.preload()
    logger.info("Catalog loaded: {}", counts)

    try:
        await asyncio.to_thread(importlib.import_module, "googletrans")
    except ImportError:
        logger.warning("googletrans is not installed: /api/translate will return an error")

    if settings.WARMUP_LLM:
        # In the background: the app can serve requests while the models warm up
        task = asyncio.create_task(warm_up_models())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
