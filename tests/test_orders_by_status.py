"""GET /stats/orders-by-status — order count and total amount for each status."""

# The seed creates two accepted orders: 1515.0 + 834.0.
SEED_ACCEPTED_ORDERS, SEED_ACCEPTED_TOTAL = 2, 2349.0


def _stats(client, headers):
    body = client.get("/stats/orders-by-status", headers=headers).json()
    return body, {s["status"]: s for s in body["statuses"]}


def _order(client, headers, quantity=1):
    # HW-WIN-10 sells at 49.0
    return client.post("/orders", headers=headers, json={
        "customer_name": "Astillero Norte",
        "items": [{"sku": "HW-WIN-10", "quantity": quantity}],
    }).json()


def _set_status(client, headers, order_id, status):
    client.patch(f"/orders/{order_id}/status", headers=headers, json={"status": status})


def test_requires_auth(client):
    assert client.get("/stats/orders-by-status").status_code == 401


def test_seed(client, api_key_headers):
    body, by_status = _stats(client, api_key_headers)
    assert body["total_orders"] == SEED_ACCEPTED_ORDERS
    assert by_status["accepted"] == {"status": "accepted", "orders": SEED_ACCEPTED_ORDERS,
                                     "total": SEED_ACCEPTED_TOTAL}


def test_every_status_is_listed_in_order_even_when_empty(client, api_key_headers):
    body, by_status = _stats(client, api_key_headers)
    assert [s["status"] for s in body["statuses"]] == ["pending", "accepted", "cancelled"]
    assert by_status["pending"] == {"status": "pending", "orders": 0, "total": 0.0}
    assert by_status["cancelled"] == {"status": "cancelled", "orders": 0, "total": 0.0}


def test_orders_move_between_statuses(client, api_key_headers):
    cancelled = _order(client, api_key_headers, quantity=2)   # 98.0
    _set_status(client, api_key_headers, cancelled["id"], "cancelled")
    pending = _order(client, api_key_headers, quantity=3)     # 147.0
    _set_status(client, api_key_headers, pending["id"], "pending")

    body, by_status = _stats(client, api_key_headers)
    assert body["total_orders"] == SEED_ACCEPTED_ORDERS + 2
    assert by_status["cancelled"] == {"status": "cancelled", "orders": 1, "total": 98.0}
    assert by_status["pending"] == {"status": "pending", "orders": 1, "total": 147.0}
    assert by_status["accepted"]["orders"] == SEED_ACCEPTED_ORDERS


def test_consistent_with_other_endpoints(client, api_key_headers):
    cancelled = _order(client, api_key_headers)
    _set_status(client, api_key_headers, cancelled["id"], "cancelled")
    _order(client, api_key_headers)  # stays accepted

    body, by_status = _stats(client, api_key_headers)
    assert body["total_orders"] == client.get("/orders", headers=api_key_headers).json()["total_count"]
    # /stats/overview counts revenue from every non-cancelled order.
    revenue = client.get("/stats/overview", headers=api_key_headers).json()["revenue"]
    assert by_status["accepted"]["total"] + by_status["pending"]["total"] == revenue
