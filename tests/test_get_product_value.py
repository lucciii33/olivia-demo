"""GET /products/{id} — stock_cost_value, stock_sale_value and units_to_minimum."""

TAPE_ID = 7  # ACC-TAPE-01: 3 in stock, minimum 10, cost 6.0, sells at 14.0


def _get(client, headers, product_id=TAPE_ID):
    return client.get(f"/products/{product_id}", headers=headers)


def test_values_for_low_stock_product(client, api_key_headers):
    body = _get(client, api_key_headers).json()
    assert body["stock_cost_value"] == 18.0
    assert body["stock_sale_value"] == 42.0
    assert body["units_to_minimum"] == 7


def test_values_follow_stock_changes(client, api_key_headers):
    client.post(f"/products/{TAPE_ID}/adjust-stock", headers=api_key_headers, json={"delta": 7})
    body = _get(client, api_key_headers).json()
    assert body["quantity"] == 10
    assert body["stock_cost_value"] == 60.0
    assert body["stock_sale_value"] == 140.0
    assert body["units_to_minimum"] == 0  # exactly at minimum


def test_above_minimum_is_zero_not_negative(client, api_key_headers):
    client.post(f"/products/{TAPE_ID}/adjust-stock", headers=api_key_headers, json={"delta": 20})
    assert _get(client, api_key_headers).json()["units_to_minimum"] == 0


def test_existing_fields_are_kept(client, api_key_headers):
    body = _get(client, api_key_headers).json()
    assert body["sku"] == "ACC-TAPE-01"
    assert body["quantity"] == 3
    assert body["low_stock"] is True


def test_unknown_product(client, api_key_headers):
    assert _get(client, api_key_headers, product_id=9999).status_code == 404
