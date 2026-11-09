from ai_workflow.agents import AGENTS

SHIRT_LINE = {"product_id": "VH001", "quantity": 1, "size": "40"}


async def test_recommendation_suggests_ties_belts_and_trousers_for_a_liked_shirt(make_state):
    out = await AGENTS["recommendation"].run(make_state("show me matches", liked_products=["VH001"]))

    recommendations = out["recommendations"]
    assert recommendations
    assert {r["category"] for r in recommendations} <= {"Ties", "Belts", "Trousers"}
    assert all(r["reasoning"] for r in recommendations)


async def test_recommendation_result_is_stored_under_its_result_key(make_state):
    out = await AGENTS["recommendation"].run(make_state("suggest something"))

    assert set(out) == {"recommendations", "agent_calls"}
    assert out["agent_calls"][0]["agent"] == "recommendation"
    assert out["agent_calls"][0]["status"] == "success"


async def test_inventory_reports_stock_for_the_cart_item(make_state):
    out = await AGENTS["inventory"].run(make_state("is it in stock?", cart=[SHIRT_LINE]))

    status = out["inventory_status"]
    assert status["available"] is True
    assert status["store"] == "Bandra Store"
    assert status["stock"] == 3


async def test_inventory_offers_alternatives_when_out_of_stock(make_state):
    cart = [{"product_id": "VH001B", "quantity": 1, "size": "40"}]  # sold out in every store

    out = await AGENTS["inventory"].run(make_state("is it available?", cart=cart))

    status = out["inventory_status"]
    assert status["available"] is False
    assert status["alternatives"]


async def test_payment_agent_needs_approval_and_charges_the_discounted_total(make_state):
    assert AGENTS["payment"].needs_approval is True

    out = await AGENTS["payment"].run(make_state("checkout", cart=[SHIRT_LINE]))

    payment = out["payment_status"]
    assert payment["success"] is True
    assert payment["gateway"] == "UPI Direct"
    assert payment["amount"] == 2250  # Rs 2500 minus 250 loyalty points (10% cap)
    assert payment["order_id"].startswith("ORD")


async def test_payment_agent_does_not_charge_an_empty_cart(make_state):
    out = await AGENTS["payment"].run(make_state("checkout"))

    assert out["payment_status"]["success"] is False
    assert out["payment_status"]["status"] == "no_items"


async def test_fulfillment_uses_real_cart_value_for_free_delivery(make_state):
    cart = [{"product_id": "VH003", "quantity": 2, "size": "40"}]  # 2 x Rs 2600

    out = await AGENTS["fulfillment"].run(make_state("when will it be delivered", cart=cart))

    assert out["fulfillment_info"]["recommended"] == "standard"
    assert out["fulfillment_info"]["timeline"] == "2-3 days"


async def test_loyalty_applies_bundle_discount_to_real_prices(make_state):
    cart = [
        {"product_id": "VH001", "quantity": 1},
        {"product_id": "VH004", "quantity": 1},
        {"product_id": "VH006", "quantity": 1},
    ]

    out = await AGENTS["loyalty"].run(make_state("any offers?", cart=cart))

    info = out["loyalty_info"]
    assert info["original_price"] == 4500
    assert info["discount_amount"] == 900
    assert info["final_price"] == 3600  # 4500 - 900, points not used unless chosen


async def test_support_explains_the_return_policy(make_state):
    out = await AGENTS["support"].run(make_state("I want to return this shirt"))

    assert out["support_info"]["status"] == "eligible"
    assert out["support_info"]["return_window"] == "30 days"
