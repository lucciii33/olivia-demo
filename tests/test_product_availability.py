"""GET /products/{id}/availability — can this many units be sold right now?"""

MAINSAIL_ID = 1  # SAIL-MAIN-052: 10 in stock, minimum 4, sells at 720.0


def _avail(client, headers, quantity, product_id=MAINSAIL_ID):
    return client.get(f"/products/{product_id}/availability", headers=headers,
                      params={"quantity": quantity})


def test_requires_auth(client):
    assert client.get(f"/products/{MAINSAIL_ID}/availability?quantity=1").status_code == 401


def test_can_fulfill(client, api_key_headers):
    assert _avail(client, api_key_headers, 2).json() == {
        "product_id": MAINSAIL_ID, "sku": "SAIL-MAIN-052", "requested": 2, "available": 10,
        "can_fulfill": True, "shortfall": 0, "low_stock_after": False,
        "line_total": 1440.0, "currency": "USD",
    }


def test_low_stock_after_boundary(client, api_key_headers):
    assert _avail(client, api_key_headers, 5).json()["low_stock_after"] is False  # 5 left
    assert _avail(client, api_key_headers, 6).json()["low_stock_after"] is True   # 4 left = minimum


def test_exactly_all_the_stock(client, api_key_headers):
    body = _avail(client, api_key_headers, 10).json()
    assert body["can_fulfill"] is True
    assert body["shortfall"] == 0
    assert body["low_stock_after"] is True


def test_cannot_fulfill(client, api_key_headers):
    body = _avail(client, api_key_headers, 13).json()
    assert body["can_fulfill"] is False
    assert body["shortfall"] == 3
    assert body["low_stock_after"] is None
    assert body["line_total"] == 9360.0


def test_quantity_is_required_and_bounded(client, api_key_headers):
    assert client.get(f"/products/{MAINSAIL_ID}/availability",
                      headers=api_key_headers).status_code == 422
    for quantity in (0, -1, 10001):
        assert _avail(client, api_key_headers, quantity).status_code == 422, quantity
    assert _avail(client, api_key_headers, 10000).status_code == 200


def test_does_not_change_stock(client, api_key_headers):
    _avail(client, api_key_headers, 5)
    assert client.get(f"/products/{MAINSAIL_ID}", headers=api_key_headers).json()["quantity"] == 10


def test_unknown_product(client, api_key_headers):
    assert _avail(client, api_key_headers, 1, product_id=9999).status_code == 404
