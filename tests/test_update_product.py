"""PUT /products/{product_id} — the response now lists the fields the request set."""

PRODUCT_ID = 1  # Mainsail Dacron 5.2m


def _put(client, headers, body, product_id=PRODUCT_ID):
    return client.put(f"/products/{product_id}", headers=headers, json=body)


def test_requires_auth(client):
    assert client.put(f"/products/{PRODUCT_ID}", json={"sale_price": 1}).status_code == 401


def test_lists_the_updated_fields(client, api_key_headers):
    body = _put(client, api_key_headers, {"sale_price": 755.0, "quantity": 11}).json()
    assert body["updated_fields"] == ["quantity", "sale_price"]
    assert body["sale_price"] == 755.0
    assert body["quantity"] == 11


def test_updated_at_is_not_listed(client, api_key_headers):
    body = _put(client, api_key_headers, {"name": "Mainsail nueva"}).json()
    assert body["updated_fields"] == ["name"]


def test_null_values_are_not_listed(client, api_key_headers):
    body = _put(client, api_key_headers, {"description": None, "unit": "pieza"}).json()
    assert body["updated_fields"] == ["unit"]


def test_empty_body_changes_nothing(client, api_key_headers):
    before = client.get(f"/products/{PRODUCT_ID}", headers=api_key_headers).json()
    body = _put(client, api_key_headers, {}).json()
    assert body["updated_fields"] == []
    assert {k: v for k, v in body.items() if k != "updated_fields"} == before


def test_product_fields_are_unchanged(client, api_key_headers):
    by_id = client.get(f"/products/{PRODUCT_ID}", headers=api_key_headers).json()
    body = _put(client, api_key_headers, {"minimum_stock": 4}).json()
    assert set(body) == set(by_id) | {"updated_fields"}


def test_unknown_product_is_404(client, api_key_headers):
    assert _put(client, api_key_headers, {"name": "x"}, product_id=999).status_code == 404
