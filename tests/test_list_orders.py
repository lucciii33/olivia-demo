"""GET /orders — total_count counts every matching order, ignoring limit and offset."""

SEED_ORDERS = 2


def _orders(client, headers, query=""):
    return client.get(f"/orders{query}", headers=headers).json()


def test_requires_auth(client):
    assert client.get("/orders").status_code == 401


def test_total_count_matches_count_on_a_full_page(client, api_key_headers):
    body = _orders(client, api_key_headers)
    assert body["count"] == SEED_ORDERS
    assert body["total_count"] == SEED_ORDERS


def test_total_count_ignores_limit(client, api_key_headers):
    body = _orders(client, api_key_headers, "?limit=1")
    assert body["count"] == 1
    assert body["total_count"] == SEED_ORDERS


def test_total_count_ignores_offset(client, api_key_headers):
    body = _orders(client, api_key_headers, "?offset=5")
    assert body["count"] == 0
    assert body["items"] == []
    assert body["total_count"] == SEED_ORDERS


def test_total_count_respects_status_filter(client, api_key_headers):
    order = client.post("/orders", headers=api_key_headers, json={
        "customer_name": "Astillero Norte",
        "items": [{"sku": "HW-WIN-10", "quantity": 1}],
    }).json()
    client.patch(f"/orders/{order['id']}/status", headers=api_key_headers,
                 json={"status": "cancelled"})

    assert _orders(client, api_key_headers)["total_count"] == SEED_ORDERS + 1
    cancelled = _orders(client, api_key_headers, "?status=cancelled&limit=10")
    assert cancelled["total_count"] == 1
    assert [o["id"] for o in cancelled["items"]] == [order["id"]]


def test_existing_fields_are_unchanged(client, api_key_headers):
    body = _orders(client, api_key_headers)
    assert set(body) == {"count", "total_count", "items"}
    assert {"id", "order_number", "customer_name", "status", "total"} <= body["items"][0].keys()
