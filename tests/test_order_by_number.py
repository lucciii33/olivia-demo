"""GET /orders/by-number/{order_number} — look an order up by its ORD-YYYY-NNNN number."""

ORDER_ID = 1


def _number(client, headers, order_id=ORDER_ID):
    return client.get(f"/orders/{order_id}", headers=headers).json()["order_number"]


def test_requires_auth(client, api_key_headers):
    number = _number(client, api_key_headers)
    assert client.get(f"/orders/by-number/{number}").status_code == 401


def test_same_body_as_lookup_by_id(client, api_key_headers):
    number = _number(client, api_key_headers)
    by_number = client.get(f"/orders/by-number/{number}", headers=api_key_headers)
    by_id = client.get(f"/orders/{ORDER_ID}", headers=api_key_headers)
    assert by_number.status_code == 200
    assert by_number.json() == by_id.json()
    assert by_number.json()["customer_name"] == "Blue Marina SL"
    assert by_number.json()["items_count"] == 2


def test_new_orders_are_found(client, api_key_headers):
    created = client.post("/orders", headers=api_key_headers, json={
        "customer_name": "Astillero Norte",
        "items": [{"sku": "HW-WIN-10", "quantity": 1}],
    }).json()
    body = client.get(f"/orders/by-number/{created['order_number']}", headers=api_key_headers).json()
    assert body["id"] == created["id"]


def test_unknown_number_is_404(client, api_key_headers):
    res = client.get("/orders/by-number/ORD-1999-9999", headers=api_key_headers)
    assert res.status_code == 404
    assert "ORD-1999-9999" in res.json()["detail"]


def test_match_is_exact(client, api_key_headers):
    number = _number(client, api_key_headers)
    for partial in (number[:-1], number.lower()):
        assert client.get(f"/orders/by-number/{partial}", headers=api_key_headers).status_code == 404


def test_other_order_routes_still_work(client, api_key_headers):
    assert client.get(f"/orders/{ORDER_ID}", headers=api_key_headers).status_code == 200
    assert client.get("/orders/search", headers=api_key_headers).status_code == 200
    res = client.patch(f"/orders/{ORDER_ID}/status", headers=api_key_headers,
                       json={"status": "pending"})
    assert res.status_code == 200
