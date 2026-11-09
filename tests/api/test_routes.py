def _create_session(client):
    return client.post("/api/session/create?customer_id=CUST001").json()["session_id"]


def test_session_create_returns_the_session_id(client):
    response = client.post("/api/session/create?customer_id=CUST001")

    body = response.json()
    assert response.status_code == 200
    assert body["session_id"].startswith("SESSION_")
    assert body["customer_id"] == "CUST001"
    assert body["message"]


def test_cart_add_ignores_the_name_and_price_sent_by_the_page(client):
    session_id = _create_session(client)

    response = client.post("/api/cart/add", json={
        "session_id": session_id, "product_id": "VH001", "quantity": 2, "size": "40",
        "product_name": "Anything", "price": 1,
    })

    assert response.json()["success"] is True
    assert response.json()["cart"] == [{"product_id": "VH001", "quantity": 2, "size": "40"}]


def test_chat_returns_a_reply_with_no_pending_approval(client):
    session_id = _create_session(client)

    response = client.post("/api/chat", json={"session_id": session_id, "message": "hello", "channel": "web"})

    assert response.status_code == 200
    assert response.json()["response"].startswith("Hello!")
    assert response.json()["pending_approval"] is None


def test_order_complete_returns_an_order_id_after_a_payment(client):
    session_id = _create_session(client)
    client.post("/api/cart/add", json={"session_id": session_id, "product_id": "VH001", "quantity": 1})
    client.post("/api/payment/process", json={"session_id": session_id, "method": "upi"})

    response = client.post("/api/order/complete", json={
        "session_id": session_id, "payment_method": "upi", "store": "Bandra Store", "kiosk": "#2",
    })

    assert response.json()["success"] is True
    assert response.json()["order_id"].startswith("ORD")
    assert client.get(f"/api/cart/{session_id}").json()["items"] == []


def test_cart_endpoint_returns_names_prices_and_total(client):
    session_id = _create_session(client)
    client.post("/api/cart/add", json={"session_id": session_id, "product_id": "VH001", "quantity": 2})

    body = client.get(f"/api/cart/{session_id}").json()

    assert body["total"] == 5000
    assert body["items"][0]["name"] == "Classic Blue Formal Shirt"


def test_order_complete_needs_a_payment_first(client):
    session_id = _create_session(client)
    client.post("/api/cart/add", json={"session_id": session_id, "product_id": "VH001", "quantity": 1})

    response = client.post("/api/order/complete", json={"session_id": session_id, "total": 1})

    assert response.status_code == 402


def test_payment_charges_the_server_price_and_repeats_return_the_first_result(client):
    session_id = _create_session(client)
    client.post("/api/cart/add", json={"session_id": session_id, "product_id": "VH001", "quantity": 1})
    body = {"session_id": session_id, "amount": 1, "method": "upi"}

    first = client.post("/api/payment/process", json=body, headers={"Idempotency-Key": "pay-1"}).json()
    again = client.post("/api/payment/process", json=body, headers={"Idempotency-Key": "pay-1"}).json()

    assert first["success"] is True
    assert first["amount"] == 2500  # one item, no offer, points not used unless chosen
    assert again == first


def test_payment_with_an_empty_cart_is_rejected(client):
    session_id = _create_session(client)

    response = client.post("/api/payment/process", json={"session_id": session_id, "amount": 5000})

    assert response.status_code == 400


def test_unknown_products_and_bad_quantities_are_rejected(client):
    session_id = _create_session(client)

    unknown = client.post("/api/cart/add", json={"session_id": session_id, "product_id": "NOPE"})
    zero = client.post("/api/cart/add", json={"session_id": session_id, "product_id": "VH001", "quantity": 0})

    assert unknown.status_code == 404
    assert zero.status_code == 422


def test_requests_need_the_session_token_when_auth_is_enabled(client, monkeypatch):
    from ai_workflow.settings import settings
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    created = client.post("/api/session/create?customer_id=CUST001").json()
    cart_url = f"/api/cart/{created['session_id']}"

    assert client.get(cart_url).status_code == 401
    assert client.get(cart_url, headers={"X-Session-Token": "wrong"}).status_code == 401
    assert client.get(cart_url, headers={"X-Session-Token": created["token"]}).status_code == 200


def test_too_many_requests_get_429(client, monkeypatch):
    from ai_workflow.settings import settings
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 2)

    codes = [client.post("/api/translate", json={"text": ""}).status_code for _ in range(3)]

    assert codes == [400, 400, 429]


def test_health_reports_redis_and_postgres(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "redis": "ok", "postgres": "disabled"}


def test_creating_a_fresh_session_starts_with_an_empty_cart(client):
    first = _create_session(client)
    client.post("/api/cart/add", json={"session_id": first, "product_id": "VH001", "quantity": 1})

    continued = client.post("/api/session/create?customer_id=CUST001").json()["session_id"]
    fresh = client.post("/api/session/create?customer_id=CUST001&fresh=true").json()["session_id"]

    assert len(client.get(f"/api/cart/{continued}").json()["items"]) == 1
    assert client.get(f"/api/cart/{fresh}").json()["items"] == []


def test_cart_endpoint_returns_the_price_the_customer_will_pay(client):
    session_id = _create_session(client)
    client.post("/api/cart/add", json={"session_id": session_id, "product_id": "VH003", "quantity": 1})
    client.post("/api/cart/add", json={"session_id": session_id, "product_id": "VH004", "quantity": 1})

    pricing = client.get(f"/api/cart/{session_id}").json()["pricing"]

    assert pricing["original_price"] == 3400
    assert pricing["discount_amount"] == 340   # multi-buy, 10%
    assert pricing["points_used"] == 0         # points are only used when the customer chooses
    assert pricing["points_usable"] == 340     # 10% of the cart
    assert pricing["final_price"] == 3060


def test_reserving_at_a_store_alerts_the_associate_who_can_accept_it(client):
    session_id = _create_session(client)
    client.post("/api/cart/add", json={"session_id": session_id, "product_id": "VH003", "quantity": 1})

    client.post(f"/api/store/reserve?session_id={session_id}&store_name=Powai Store")
    alert = client.get(f"/api/session/{session_id}").json()["store_alert"]
    assert alert["kind"] == "reservation"
    assert alert["store"] == "Powai Store"
    assert alert["items"] == ["Light Pink Formal Shirt"]
    assert alert["status"] == "pending"

    client.post(f"/api/store/alert/respond?session_id={session_id}&action=accept")
    assert client.get(f"/api/session/{session_id}").json()["store_alert"]["status"] == "accepted"


def test_rejecting_a_reservation_clears_the_reserved_store(client):
    session_id = _create_session(client)
    client.post(f"/api/store/reserve?session_id={session_id}&store_name=Powai Store")

    client.post(f"/api/store/alert/respond?session_id={session_id}&action=reject")

    session = client.get(f"/api/session/{session_id}").json()
    assert session["store_alert"]["status"] == "rejected"
    assert session["reserved_store"] is None


def test_paying_after_reserving_tells_the_store_to_expect_a_pickup(client):
    session_id = _create_session(client)
    client.post("/api/cart/add", json={"session_id": session_id, "product_id": "VH003", "quantity": 1})
    client.post(f"/api/store/reserve?session_id={session_id}&store_name=Powai Store")
    client.post("/api/payment/process", json={"session_id": session_id, "method": "upi"})

    client.post("/api/order/complete", json={"session_id": session_id, "payment_method": "upi", "store": "Powai Store"})

    alert = client.get(f"/api/session/{session_id}").json()["store_alert"]
    assert alert["kind"] == "pickup"
    assert alert["store"] == "Powai Store"
    assert alert["order_id"].startswith("ORD")


def test_responding_with_nothing_waiting_is_a_404(client):
    session_id = _create_session(client)

    response = client.post(f"/api/store/alert/respond?session_id={session_id}&action=accept")

    assert response.status_code == 404


def test_loyalty_points_are_only_used_after_the_customer_chooses_them(client):
    session_id = _create_session(client)
    client.post("/api/cart/add", json={"session_id": session_id, "product_id": "VH002", "quantity": 1})

    before = client.get(f"/api/cart/{session_id}").json()["pricing"]
    chosen = client.post(f"/api/cart/points?session_id={session_id}&use=true").json()["pricing"]
    after = client.get(f"/api/cart/{session_id}").json()["pricing"]
    payment = client.post("/api/payment/process", json={"session_id": session_id, "method": "upi"}).json()

    assert before["final_price"] == 2800
    assert chosen["final_price"] == 2520
    assert after["final_price"] == 2520
    assert payment["amount"] == 2520


def test_a_sold_out_product_cannot_be_added_and_similar_items_are_offered(client):
    session_id = _create_session(client)

    response = client.post("/api/cart/add", json={"session_id": session_id, "product_id": "VH001B", "quantity": 1})

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "out of stock" in detail["message"]
    assert detail["alternatives"]
    assert all(item["product_id"] != "VH001B" for item in detail["alternatives"])
    assert client.get(f"/api/cart/{session_id}").json()["items"] == []


def test_availability_lists_which_products_can_be_bought(client):
    availability = client.get("/api/products/availability").json()["availability"]

    assert availability["VH002"] is True
    assert availability["VH001B"] is False
