"""GET /stats/stock-by-unit — stock grouped by unit of measure."""

# Seed: 5 products in "unit" (10+7+5+230+18 = 270), Dyneema in "meter" (60, low),
# tape and telltales in "box" (3+41 = 44, tape is low).
SEED = [
    {"unit": "box", "products": 2, "quantity": 44, "low_stock_products": 1},
    {"unit": "meter", "products": 1, "quantity": 60, "low_stock_products": 1},
    {"unit": "unit", "products": 5, "quantity": 270, "low_stock_products": 0},
]


def _by_unit(client, headers):
    return client.get("/stats/stock-by-unit", headers=headers)


def test_requires_auth(client):
    assert client.get("/stats/stock-by-unit").status_code == 401


def test_needs_no_parameters(client, api_key_headers):
    assert _by_unit(client, api_key_headers).status_code == 200


def test_seed_groups(client, api_key_headers):
    assert _by_unit(client, api_key_headers).json() == {"count": 3, "units": SEED}


def test_totals_match_the_products(client, api_key_headers):
    products = client.get("/products?limit=100", headers=api_key_headers).json()["items"]
    units = _by_unit(client, api_key_headers).json()["units"]
    assert sum(u["products"] for u in units) == len(products)
    assert sum(u["quantity"] for u in units) == sum(p["quantity"] for p in products)
    assert sum(u["low_stock_products"] for u in units) == sum(p["low_stock"] for p in products)


def test_new_unit_shows_up(client, api_key_headers):
    client.post("/products", headers=api_key_headers,
                json={"name": "Resina", "sku": "RES-1", "unit": "kg", "quantity": 12, "minimum_stock": 2})
    body = _by_unit(client, api_key_headers).json()
    assert body["count"] == 4
    assert {"unit": "kg", "products": 1, "quantity": 12, "low_stock_products": 0} in body["units"]
