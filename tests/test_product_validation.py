"""POST /products and PUT /products/{id} — 201, SKU normalising and field validation."""


def _create(client, headers, **fields):
    return client.post("/products", headers=headers,
                       json={"name": "Producto QA", "sku": "QA-001", **fields})


def test_create_returns_201(client, api_key_headers):
    res = _create(client, api_key_headers)
    assert res.status_code == 201
    assert res.json()["sku"] == "QA-001"


def test_sku_and_name_are_trimmed_and_sku_upper_cased(client, api_key_headers):
    body = _create(client, api_key_headers, name="  Producto QA  ", sku="  qa-002 ").json()
    assert body["sku"] == "QA-002"
    assert body["name"] == "Producto QA"


def test_duplicate_sku_ignores_case_and_spaces(client, api_key_headers):
    res = _create(client, api_key_headers, sku=" sail-main-052 ")
    assert res.status_code == 409
    assert res.json()["detail"] == "SKU 'SAIL-MAIN-052' already exists"


def test_blank_name_or_sku(client, api_key_headers):
    for fields in ({"name": ""}, {"sku": ""}, {"name": "   "}, {"sku": "   "}):
        assert _create(client, api_key_headers, **fields).status_code == 422, fields


def test_sku_max_length(client, api_key_headers):
    assert _create(client, api_key_headers, sku="X" * 32).status_code == 201
    assert _create(client, api_key_headers, sku="Y" * 33).status_code == 422


def test_negative_numbers_are_rejected(client, api_key_headers):
    for field in ("quantity", "minimum_stock", "cost_price", "sale_price"):
        assert _create(client, api_key_headers, **{field: -1}).status_code == 422, field
    assert _create(client, api_key_headers, quantity=0, sale_price=0).status_code == 201


def test_currency_must_be_three_capital_letters(client, api_key_headers):
    for currency in ("usd", "US", "EURO", "U$D"):
        assert _create(client, api_key_headers, currency=currency).status_code == 422, currency
    assert _create(client, api_key_headers, currency="EUR").json()["currency"] == "EUR"


def test_sale_price_below_cost_is_allowed(client, api_key_headers):
    res = _create(client, api_key_headers, cost_price=10, sale_price=5)
    assert res.status_code == 201


def test_update_validates_the_same_way(client, api_key_headers):
    for fields in ({"quantity": -1}, {"minimum_stock": -5}, {"cost_price": -0.01},
                   {"sale_price": -1}, {"currency": "eur"}, {"name": ""}):
        res = client.put("/products/1", headers=api_key_headers, json=fields)
        assert res.status_code == 422, fields
    assert client.get("/products/1", headers=api_key_headers).json()["quantity"] == 10


def test_update_still_accepts_valid_values(client, api_key_headers):
    res = client.put("/products/1", headers=api_key_headers, json={"quantity": 0, "currency": "EUR"})
    assert res.status_code == 200
    assert res.json()["updated_fields"] == ["quantity", "currency"]
