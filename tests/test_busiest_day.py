"""GET /stats/busiest-day — orders and revenue per day, and the busiest one."""
from datetime import datetime, timezone

import db

SEED_ORDERS, SEED_REVENUE = 2, 2349.0


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _busiest(client, headers):
    return client.get("/stats/busiest-day", headers=headers)


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
    assert client.get("/stats/busiest-day").status_code == 401


def test_needs_no_parameters(client, api_key_headers):
    assert _busiest(client, api_key_headers).status_code == 200


def test_seed_lands_on_one_day(client, api_key_headers):
    body = _busiest(client, api_key_headers).json()
    assert body["count"] == 1
    assert body["busiest_day"] == {"day": _today(), "orders": SEED_ORDERS, "revenue": SEED_REVENUE}
    assert body["days"] == [body["busiest_day"]]


def test_days_are_chronological_and_busiest_wins(client, api_key_headers):
    old = _order(client, api_key_headers)
    _backdate(old["id"], "2024-02-10T10:00:00+00:00")
    other = _order(client, api_key_headers)
    _backdate(other["id"], "2024-02-11T10:00:00+00:00")

    body = _busiest(client, api_key_headers).json()
    assert [d["day"] for d in body["days"]] == ["2024-02-10", "2024-02-11", _today()]
    assert body["busiest_day"]["day"] == _today()  # the seed day has 2 orders
    assert body["busiest_day"]["orders"] == SEED_ORDERS


def test_a_busier_day_takes_over(client, api_key_headers):
    for _ in range(3):
        order = _order(client, api_key_headers)
        _backdate(order["id"], "2024-03-05T09:00:00+00:00")
    body = _busiest(client, api_key_headers).json()
    assert body["busiest_day"] == {"day": "2024-03-05", "orders": 3, "revenue": 147.0}


def test_cancelled_orders_do_not_count(client, api_key_headers):
    order = _order(client, api_key_headers)
    client.patch(f"/orders/{order['id']}/status", headers=api_key_headers,
                 json={"status": "cancelled"})
    body = _busiest(client, api_key_headers).json()
    assert body["busiest_day"]["orders"] == SEED_ORDERS
    assert body["busiest_day"]["revenue"] == SEED_REVENUE
