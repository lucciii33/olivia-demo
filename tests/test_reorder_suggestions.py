"""GET /products/reorder-suggestions — what to restock, how much, and at what cost."""

# Seed stock below minimum (restock target is twice the minimum):
#   ACC-TAPE-01   3 of 10  -> order 17 x cost 6.0 = 102.0
#   LINE-DYN-06  60 of 100 -> order 140 x cost 2.1 = 294.0


def _suggestions(client, headers):
    return client.get("/products/reorder-suggestions", headers=headers)


def test_requires_auth(client):
    assert client.get("/products/reorder-suggestions").status_code == 401


def test_needs_no_parameters(client, api_key_headers):
    # Also guards the route order: after /products/{product_id} this would be a 422.
    assert _suggestions(client, api_key_headers).status_code == 200


def test_seed_suggestions(client, api_key_headers):
    body = _suggestions(client, api_key_headers).json()
    assert body["count"] == 2
    assert body["estimated_cost"] == 396.0
    assert body["currency"] == "USD"
    assert [(i["sku"], i["suggested_order"], i["estimated_cost"]) for i in body["items"]] == [
        ("ACC-TAPE-01", 17, 102.0),
        ("LINE-DYN-06", 140, 294.0),
    ]


def test_matches_the_low_stock_list(client, api_key_headers):
    low = client.get("/products/low-stock", headers=api_key_headers).json()["items"]
    body = _suggestions(client, api_key_headers).json()
    assert [i["id"] for i in body["items"]] == [p["id"] for p in low]


def test_following_the_suggestion_clears_the_list(client, api_key_headers):
    items = _suggestions(client, api_key_headers).json()["items"]
    client.post("/products/bulk-adjust", headers=api_key_headers, json={
        "items": [{"sku": i["sku"], "delta": i["suggested_order"]} for i in items],
    })
    body = _suggestions(client, api_key_headers).json()
    assert body == {"count": 0, "estimated_cost": 0, "currency": "USD", "items": []}


def test_skips_products_with_zero_minimum_and_stock(client, api_key_headers):
    # Counts as low stock (0 <= 0), but there is nothing to order.
    created = client.post("/products", headers=api_key_headers,
                          json={"name": "Sin minimo", "sku": "ZERO-1"}).json()
    assert created["low_stock"] is True
    ids = [i["id"] for i in _suggestions(client, api_key_headers).json()["items"]]
    assert created["id"] not in ids


def test_get_product_by_id_still_works(client, api_key_headers):
    assert client.get("/products/1", headers=api_key_headers).status_code == 200
