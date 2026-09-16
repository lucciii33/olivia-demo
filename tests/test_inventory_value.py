"""GET /stats/inventory-value — stock valued at cost and at sale price."""


def _value(client, headers):
    return client.get("/stats/inventory-value", headers=headers).json()


def _expected(client, headers):
    products = client.get("/products?limit=100", headers=headers).json()["items"]
    cost = round(sum(p["quantity"] * p["cost_price"] for p in products), 2)
    retail = round(sum(p["quantity"] * p["sale_price"] for p in products), 2)
    return len(products), cost, retail


def test_requires_auth(client):
    assert client.get("/stats/inventory-value").status_code == 401


def test_needs_no_parameters(client, api_key_headers):
    assert client.get("/stats/inventory-value", headers=api_key_headers).status_code == 200


def test_values_match_the_products(client, api_key_headers):
    count, cost, retail = _expected(client, api_key_headers)
    assert _value(client, api_key_headers) == {
        "products": count,
        "cost_value": cost,
        "retail_value": retail,
        "potential_margin": round(retail - cost, 2),
        "currency": "USD",
    }


def test_cost_value_matches_overview(client, api_key_headers):
    overview = client.get("/stats/overview", headers=api_key_headers).json()
    assert _value(client, api_key_headers)["cost_value"] == overview["inventory_cost_value"]


def test_restocking_raises_the_value(client, api_key_headers):
    before = _value(client, api_key_headers)
    # Sail Repair Tape (id 7): cost 6.0, sale 14.0
    client.post("/products/7/adjust-stock", headers=api_key_headers, json={"delta": 10})
    after = _value(client, api_key_headers)
    assert round(after["cost_value"] - before["cost_value"], 2) == 60.0
    assert round(after["retail_value"] - before["retail_value"], 2) == 140.0
