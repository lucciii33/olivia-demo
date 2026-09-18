"""GET /stats/product-margins — margin per product, highest first."""


def _margins(client, headers):
    return client.get("/stats/product-margins", headers=headers)


def test_requires_auth(client):
    assert client.get("/stats/product-margins").status_code == 401


def test_needs_no_parameters(client, api_key_headers):
    assert _margins(client, api_key_headers).status_code == 200


def test_seed_ranking(client, api_key_headers):
    body = _margins(client, api_key_headers).json()
    assert body["count"] == 8
    assert body["currency"] == "USD"
    # Telltales: cost 1.5, sale 6.0 -> 4.5 margin, 75%. Mainsail: 380 -> 720, 47.2%.
    first, last = body["items"][0], body["items"][-1]
    assert (first["sku"], first["margin"], first["margin_percent"]) == ("ACC-TELL-01", 4.5, 75.0)
    assert (last["sku"], last["margin"], last["margin_percent"]) == ("SAIL-MAIN-052", 340.0, 47.2)
    percents = [i["margin_percent"] for i in body["items"]]
    assert percents == sorted(percents, reverse=True)


def test_margin_is_sale_minus_cost(client, api_key_headers):
    for item in _margins(client, api_key_headers).json()["items"]:
        assert item["margin"] == round(item["sale_price"] - item["cost_price"], 2)


def test_covers_every_product(client, api_key_headers):
    products = client.get("/products?limit=100", headers=api_key_headers).json()["items"]
    ids = [i["id"] for i in _margins(client, api_key_headers).json()["items"]]
    assert sorted(ids) == sorted(p["id"] for p in products)


def test_products_without_price_go_last(client, api_key_headers):
    created = client.post("/products", headers=api_key_headers,
                          json={"name": "Sin precio", "sku": "FREE-1"}).json()
    last = _margins(client, api_key_headers).json()["items"][-1]
    assert last["id"] == created["id"]
    assert last["margin"] == 0
    assert last["margin_percent"] is None


def test_average_margin_percent(client, api_key_headers):
    body = _margins(client, api_key_headers).json()
    percents = [i["margin_percent"] for i in body["items"]]
    assert body["average_margin_percent"] == round(sum(percents) / len(percents), 1)
    assert body["average_margin_percent"] == 55.8


def test_average_ignores_products_without_price(client, api_key_headers):
    before = _margins(client, api_key_headers).json()["average_margin_percent"]
    client.post("/products", headers=api_key_headers, json={"name": "Sin precio", "sku": "FREE-2"})
    assert _margins(client, api_key_headers).json()["average_margin_percent"] == before

