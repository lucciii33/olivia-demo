"""GET /stats/sales-by-month — non-cancelled sales grouped by calendar month."""
from datetime import datetime, timezone

import db

# From the seed in db.py: two accepted orders created at startup.
# ORD-...-0001: 2 mainsails + 10 shackles = 12 units, 1515.0
# ORD-...-0002: 1 genoa + 4 telltales    =  5 units,  834.0
SEED_ORDERS = 2
SEED_UNITS = 17
SEED_REVENUE = 2349.0
WINCH_SKU = "HW-WIN-10"  # sale_price 49.0


def _this_month():
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _order(client, headers, quantity=1):
    return client.post("/orders", headers=headers, json={
        "customer_name": "Astillero Norte",
        "items": [{"sku": WINCH_SKU, "quantity": quantity}],
    }).json()


def _backdate(order_id, iso_timestamp):
    conn = db.get_conn()
    try:
        conn.execute("UPDATE orders SET created_at = ? WHERE id = ?", (iso_timestamp, order_id))
        conn.commit()
    finally:
        conn.close()


def test_requires_auth(client):
    assert client.get("/stats/sales-by-month").status_code == 401


def test_seed_lands_in_current_month(client, api_key_headers):
    body = client.get("/stats/sales-by-month", headers=api_key_headers).json()
    assert body["year"] is None
    assert body["months"] == [{
        "month": _this_month(),
        "orders": SEED_ORDERS,
        "units_sold": SEED_UNITS,
        "revenue": SEED_REVENUE,
    }]
    assert body["totals"] == {"orders": SEED_ORDERS, "units_sold": SEED_UNITS,
                              "revenue": SEED_REVENUE}


def test_cancelled_orders_do_not_count(client, api_key_headers):
    order = _order(client, api_key_headers, quantity=3)
    client.patch(f"/orders/{order['id']}/status", headers=api_key_headers,
                 json={"status": "cancelled"})
    totals = client.get("/stats/sales-by-month", headers=api_key_headers).json()["totals"]
    assert totals == {"orders": SEED_ORDERS, "units_sold": SEED_UNITS, "revenue": SEED_REVENUE}


def test_months_are_chronological(client, api_key_headers):
    old = _order(client, api_key_headers, quantity=2)
    _backdate(old["id"], "2024-01-15T10:00:00+00:00")

    months = client.get("/stats/sales-by-month", headers=api_key_headers).json()["months"]
    assert [m["month"] for m in months] == ["2024-01", _this_month()]
    assert months[0] == {"month": "2024-01", "orders": 1, "units_sold": 2, "revenue": 98.0}


def test_orders_in_same_month_are_grouped(client, api_key_headers):
    for day in ("03", "28"):
        order = _order(client, api_key_headers)
        _backdate(order["id"], f"2024-02-{day}T12:00:00+00:00")

    months = client.get("/stats/sales-by-month", headers=api_key_headers).json()["months"]
    feb = next(m for m in months if m["month"] == "2024-02")
    assert feb == {"month": "2024-02", "orders": 2, "units_sold": 2, "revenue": 98.0}


def test_year_filter(client, api_key_headers):
    old = _order(client, api_key_headers, quantity=4)
    _backdate(old["id"], "2024-06-01T09:00:00+00:00")

    body = client.get("/stats/sales-by-month?year=2024", headers=api_key_headers).json()
    assert body["year"] == 2024
    assert [m["month"] for m in body["months"]] == ["2024-06"]
    assert body["totals"] == {"orders": 1, "units_sold": 4, "revenue": 196.0}


def test_year_without_sales_is_empty(client, api_key_headers):
    body = client.get("/stats/sales-by-month?year=2001", headers=api_key_headers).json()
    assert body["months"] == []
    assert body["totals"] == {"orders": 0, "units_sold": 0, "revenue": 0}


def test_year_out_of_range_is_422(client, api_key_headers):
    for bad in ("1999", "2101", "abc"):
        res = client.get(f"/stats/sales-by-month?year={bad}", headers=api_key_headers)
        assert res.status_code == 422, bad
