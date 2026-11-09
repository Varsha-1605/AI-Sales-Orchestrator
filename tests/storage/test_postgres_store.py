"""These tests need a real Postgres database. Set POSTGRES_URL (docker compose up postgres) to run them."""

import pytest
import pytest_asyncio

from ai_workflow.settings import settings
from ai_workflow.storage import postgres_store

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def postgres():
    if not settings.POSTGRES_URL.get_secret_value():
        pytest.skip("POSTGRES_URL is not set")
    await postgres_store.open_postgres()
    yield
    await postgres_store.close_postgres()


async def test_an_order_can_be_saved_and_read_back(postgres):
    order = {
        "id": "ORD_TEST0001",
        "session_id": "SESSION_test",
        "customer_id": "CUST001",
        "items": [{"product_id": "VH001", "quantity": 1}],
        "total": 2250,
        "payment_method": "upi",
        "gateway": "UPI Direct",
        "transaction_id": "TXN123456",
        "store": "Bandra Store",
    }

    await postgres_store.save_order(order)
    saved = await postgres_store.get_order("ORD_TEST0001")

    assert saved["customer_id"] == "CUST001"
    assert saved["items"] == order["items"]
    assert saved["gateway"] == "UPI Direct"


async def test_preferences_are_replaced_on_each_save(postgres):
    await postgres_store.save_preferences("CUST_TEST", {"sizes": ["40"]})
    await postgres_store.save_preferences("CUST_TEST", {"sizes": ["42"]})

    assert await postgres_store.get_preferences("CUST_TEST") == {"sizes": ["42"]}
