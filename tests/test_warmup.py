from ai_workflow import warmup
from ai_workflow.graph import supervisor
from ai_workflow.storage import catalog_store


def test_preload_reads_all_three_data_files():
    counts = catalog_store.preload()

    assert counts["products"] >= 20
    assert counts["stores"] >= 3
    assert counts["customers"] >= 1


async def test_model_warmup_does_nothing_without_a_model():
    await warmup.warm_up_models()  # conftest removes every model, so there is nothing to call


async def test_a_failing_model_does_not_stop_startup(monkeypatch):
    class BrokenModel:
        async def ainvoke(self, messages):
            raise RuntimeError("network unreachable")

    monkeypatch.setattr(supervisor, "llm", BrokenModel())

    await warmup.warm_up_models()  # logs a warning and returns
