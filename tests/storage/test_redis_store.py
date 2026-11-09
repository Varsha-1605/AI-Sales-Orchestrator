from ai_workflow.settings import settings
from ai_workflow.storage import redis_store


def test_session_can_be_created_and_read_back():
    session_id = redis_store.create_session("CUST001")

    session = redis_store.get_session(session_id)

    assert session_id.startswith("SESSION_")
    assert session["customer_id"] == "CUST001"
    assert session["cart"] == []
    assert session["status"] == "active"
    assert redis_store.get_session("SESSION_missing") is None


def test_session_expires_after_the_timeout():
    session_id = redis_store.create_session("CUST001")

    ttl = redis_store._redis().ttl(f"session:{session_id}")

    assert 0 < ttl <= settings.SESSION_TIMEOUT_SECONDS


def test_cart_items_can_be_added_updated_and_removed(session_id):
    cart = redis_store.add_to_cart(session_id, "VH001", quantity=1, size="40")
    assert cart == [{"product_id": "VH001", "quantity": 1, "size": "40"}]

    cart = redis_store.update_cart_quantity(session_id, "VH001", 3)
    assert cart[0]["quantity"] == 3

    assert redis_store.remove_from_cart(session_id, "VH001") == []
    assert redis_store.get_session(session_id)["cart"] == []


def test_a_new_session_for_the_same_customer_keeps_the_cart():
    first = redis_store.create_session("CUST001")
    redis_store.add_to_cart(first, "VH001")

    second = redis_store.create_session("CUST001")

    assert redis_store._redis().get("customer:CUST001:session") == second
    assert redis_store.get_session(second)["cart"][0]["product_id"] == "VH001"


def test_rate_limit_trips_after_the_allowed_number_of_requests():
    results = [redis_store.is_rate_limited("1.2.3.4", 2) for _ in range(3)]

    assert results == [False, False, True]


def test_a_fresh_session_does_not_inherit_the_last_cart():
    first = redis_store.create_session("CUST001")
    redis_store.add_to_cart(first, "VH001")
    redis_store.add_liked_product(first, "VH001")

    second = redis_store.create_session("CUST001", carry_over=False)

    session = redis_store.get_session(second)
    assert session["cart"] == []
    assert session["liked_products"] == []
