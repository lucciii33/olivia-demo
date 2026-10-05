"""GET /stats/dead-stock — products that were never sold, most expensive first."""

# The seed sells the mainsail, shackles, genoa and telltales. What is left:
#   SAIL-SPIN-15   5 x 510.0 = 2550.0
#   HW-WIN-10     18 x  22.0 =  396.0
#   LINE-DYN-06   60 x   2.1 =  126.0
#   ACC-TAPE-01    3 x   6.0 =   18.0
SEED_SKUS = ["SAIL-SPIN-15", "HW-WIN-10", "LINE-DYN-06", "ACC-TAPE-01"]
SEED_COST_VALUE = 3090.0


def _dead(client, headers):
    return client.get("/stats/dead-stock", headers=headers)


def _sell(client, headers, sku, quantity=1):
    return client.post("/orders", headers=headers, json={
        "customer_name": "Astillero Norte",
        "items": [{"sku": sku, "quantity": quantity}],
    }).json()


def test_requires_auth(client):
    assert client.get("/stats/dead-stock").status_code == 401


def test_needs_no_parameters(client, api_key_headers):
    assert _dead(client, api_key_headers).status_code == 200


def test_seed_dead_stock(client, api_key_headers):
    body = _dead(client, api_key_headers).json()
    assert body["count"] == 4
    assert body["cost_value"] == SEED_COST_VALUE
    assert body["currency"] == "USD"
    assert [i["sku"] for i in body["items"]] == SEED_SKUS  # most money idle first
    assert body["items"][0]["cost_value"] == 2550.0


def test_selling_a_product_removes_it(client, api_key_headers):
    _sell(client, api_key_headers, "SAIL-SPIN-15")
    body = _dead(client, api_key_headers).json()
    assert "SAIL-SPIN-15" not in [i["sku"] for i in body["items"]]
    assert body["count"] == 3


def test_cancelled_sales_do_not_count_as_sold(client, api_key_headers):
    order = _sell(client, api_key_headers, "HW-WIN-10")
    client.patch(f"/orders/{order['id']}/status", headers=api_key_headers,
                 json={"status": "cancelled"})
    assert "HW-WIN-10" in [i["sku"] for i in _dead(client, api_key_headers).json()["items"]]


def test_a_brand_new_product_is_dead_stock(client, api_key_headers):
    created = client.post("/products", headers=api_key_headers, json={
        "name": "Ancla nueva", "sku": "ANC-1", "quantity": 2, "cost_price": 100.0}).json()
    body = _dead(client, api_key_headers).json()
    assert created["id"] in [i["id"] for i in body["items"]]
    assert body["cost_value"] == SEED_COST_VALUE + 200.0


def test_cost_value_is_quantity_times_cost(client, api_key_headers):
    for item in _dead(client, api_key_headers).json()["items"]:
        assert item["cost_value"] == round(item["quantity"] * item["cost_price"], 2)
