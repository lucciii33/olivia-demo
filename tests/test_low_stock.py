"""GET /products/low-stock — shortfall per product and total_shortfall."""

# ACC-TAPE-01: 3 of 10, LINE-DYN-06: 60 of 100
SEED = [("ACC-TAPE-01", 7), ("LINE-DYN-06", 40)]


def _low(client, headers):
    return client.get("/products/low-stock", headers=headers)


def _product_id(client, headers, sku):
    return client.get(f"/products/by-sku/{sku}", headers=headers).json()["id"]


def test_requires_auth(client):
    assert client.get("/products/low-stock").status_code == 401


def test_seed_shortfall(client, api_key_headers):
    body = _low(client, api_key_headers).json()
    assert body["count"] == 2
    assert [(i["sku"], i["shortfall"]) for i in body["items"]] == SEED
    assert body["total_shortfall"] == 47


def test_items_keep_their_product_fields(client, api_key_headers):
    item = _low(client, api_key_headers).json()["items"][0]
    assert item["low_stock"] is True
    assert item["shortfall"] == item["minimum_stock"] - item["quantity"]


def test_exactly_at_minimum_has_zero_shortfall(client, api_key_headers):
    pid = _product_id(client, api_key_headers, "ACC-TAPE-01")
    client.post(f"/products/{pid}/adjust-stock", headers=api_key_headers, json={"delta": 7})
    body = _low(client, api_key_headers).json()
    tape = next(i for i in body["items"] if i["sku"] == "ACC-TAPE-01")
    assert tape["shortfall"] == 0
    assert body["total_shortfall"] == 40


def test_restocked_products_drop_out(client, api_key_headers):
    pid = _product_id(client, api_key_headers, "ACC-TAPE-01")
    client.post(f"/products/{pid}/adjust-stock", headers=api_key_headers, json={"delta": 8})
    body = _low(client, api_key_headers).json()
    assert body["count"] == 1
    assert body["total_shortfall"] == 40
