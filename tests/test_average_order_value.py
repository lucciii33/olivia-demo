"""GET /stats/average-order-value — average order total, overall and per month."""
from datetime import datetime, timezone

import db

SEED_ORDERS, SEED_REVENUE = 2, 2349.0
SEED_AVERAGE = 1174.5


def _this_month():
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _aov(client, headers):
    return client.get("/stats/average-order-value", headers=headers)


def _order(client, headers, quantity=1):
    # HW-WIN-10 sells at 49.0
    return client.post("/orders", headers=headers, json={
        "customer_name": "Astillero Norte",
        "items": [{"sku": "HW-WIN-10", "quantity": quantity}],
    }).json()


def _backdate(order_id, iso_timestamp):
    conn = db.get_conn()
    try:
        conn.execute("UPDATE orders SET created_at = ? WHERE id = ?", (iso_timestamp, order_id))
        conn.commit()
    finally:
        conn.close()


def test_requires_auth(client):
    assert client.get("/stats/average-order-value").status_code == 401


def test_needs_no_parameters(client, api_key_headers):
    assert _aov(client, api_key_headers).status_code == 200


def test_seed_average(client, api_key_headers):
    body = _aov(client, api_key_headers).json()
    assert body["orders"] == SEED_ORDERS
    assert body["revenue"] == SEED_REVENUE
    assert body["average_order_value"] == SEED_AVERAGE
    assert body["currency"] == "USD"
    assert body["months"] == [{
        "month": _this_month(), "orders": SEED_ORDERS,
        "revenue": SEED_REVENUE, "average_order_value": SEED_AVERAGE,
    }]


def test_months_are_chronological_with_their_own_average(client, api_key_headers):
    for quantity in (1, 3):
        order = _order(client, api_key_headers, quantity)
        _backdate(order["id"], "2024-02-10T10:00:00+00:00")

    body = _aov(client, api_key_headers).json()
    assert [m["month"] for m in body["months"]] == ["2024-02", _this_month()]
    assert body["months"][0] == {
        "month": "2024-02", "orders": 2, "revenue": 196.0, "average_order_value": 98.0,
    }
    assert body["orders"] == SEED_ORDERS + 2
    assert body["revenue"] == SEED_REVENUE + 196.0
    # The overall figure is weighted by orders, not an average of the months.
    assert body["average_order_value"] == round((SEED_REVENUE + 196.0) / 4, 2)


def test_cancelled_orders_do_not_count(client, api_key_headers):
    order = _order(client, api_key_headers)
    client.patch(f"/orders/{order['id']}/status", headers=api_key_headers,
                 json={"status": "cancelled"})
    body = _aov(client, api_key_headers).json()
    assert body["orders"] == SEED_ORDERS
    assert body["average_order_value"] == SEED_AVERAGE


def test_no_orders_gives_zero(client, api_key_headers):
    for order in client.get("/orders", headers=api_key_headers).json()["items"]:
        client.patch(f"/orders/{order['id']}/status", headers=api_key_headers,
                     json={"status": "cancelled"})
    body = _aov(client, api_key_headers).json()
    assert body == {"orders": 0, "revenue": 0, "average_order_value": 0.0,
                    "currency": "USD", "months": []}
