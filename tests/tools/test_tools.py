from ai_workflow.tools.cart import cart_total
from ai_workflow.tools.catalog import check_stock, find_matching_products
from ai_workflow.tools.orders import loyalty_discount


def test_cart_total_uses_catalog_prices():
    cart = [{"product_id": "VH001", "quantity": 2}, {"product_id": "VH004", "quantity": 1}]

    result = cart_total(cart)

    assert result["total"] == 5800  # 2 x 2500 + 800
    assert len(result["items"]) == 2
    assert result["items"][0]["name"] == "Classic Blue Formal Shirt"
    assert result["items"][0]["line_total"] == 5000


def test_two_items_get_ten_percent_off():
    cart = [{"product_id": "VH001", "quantity": 1}, {"product_id": "VH004", "quantity": 1}]

    discount = loyalty_discount("CUST001", cart)

    assert discount["offers"] == ["Multi-buy: 10% off on 2+ items"]
    assert discount["discount_amount"] == 330
    assert discount["points_used"] == 0
    assert discount["points_usable"] == 330  # capped at 10% of 3300
    assert discount["final_price"] == 2970  # 3300 - 330
    assert loyalty_discount("CUST001", cart, use_points=True)["final_price"] == 2640  # also minus 330 points


def test_three_items_get_twenty_percent_off():
    cart = [
        {"product_id": "VH001", "quantity": 1},
        {"product_id": "VH002", "quantity": 1},
        {"product_id": "VH004", "quantity": 1},
    ]

    discount = loyalty_discount("CUST001", cart)

    assert discount["offers"] == ["Bundle Offer: 20% off on 3+ items"]
    assert discount["discount_amount"] == 1220
    assert discount["final_price"] == 4880  # 6100 - 1220
    assert loyalty_discount("CUST001", cart, use_points=True)["final_price"] == 4380  # also minus 500 points


def test_stock_lookup_finds_the_nearest_store_with_stock():
    stock = check_stock("VH001", "40", "Mumbai")

    assert stock["available"] is True
    assert stock["store"] == "Bandra Store"
    assert stock["stock"] == 3
    assert stock["distance"] == "2km"
    assert len(stock["stores"]) >= 3


def test_out_of_stock_returns_alternatives_and_restock_time():
    stock = check_stock("VH001", "44", "Mumbai")

    assert stock["available"] is False
    assert 0 < len(stock["alternatives"]) <= 2
    assert all(alt["product_id"] != "VH001" for alt in stock["alternatives"])
    assert stock["restock_date"]


def test_matching_products_for_a_shirt_are_ties_belts_trousers_with_same_color_first():
    matches = find_matching_products(["VH001"])  # a blue shirt

    assert {p["category"] for p in matches} == {"Ties", "Belts", "Trousers"}
    assert "Blue" in matches[0]["colors"]


def test_the_next_offer_says_what_one_more_item_earns():
    one = loyalty_discount("CUST001", [{"product_id": "VH001", "quantity": 1}])
    two = loyalty_discount("CUST001", [{"product_id": "VH001", "quantity": 1}, {"product_id": "VH004", "quantity": 1}])
    three = loyalty_discount("CUST001", [
        {"product_id": "VH001", "quantity": 1}, {"product_id": "VH004", "quantity": 1}, {"product_id": "VH006", "quantity": 1},
    ])

    assert one["next_offer"] == {"items_needed": 1, "discount_percent": 10}
    assert two["next_offer"] == {"items_needed": 1, "discount_percent": 20}
    assert three["next_offer"] is None
