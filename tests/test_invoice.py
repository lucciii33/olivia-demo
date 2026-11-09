"""GET /orders/{id}/invoice — subtotal, discount, tax and total, rounded step by step."""

ORDER_ID = 1  # seed: SAIL-MAIN-052 x2 @ 720.0 + HW-SHK-08 x10 @ 7.5 = 1515.0


def _invoice(client, headers, order_id=ORDER_ID, query=""):
    return client.get(f"/orders/{order_id}/invoice{query}", headers=headers)


def test_requires_auth(client):
    assert client.get(f"/orders/{ORDER_ID}/invoice").status_code == 401


def test_default_is_21_percent_tax_no_discount(client, api_key_headers):
    body = _invoice(client, api_key_headers).json()
    assert body["subtotal"] == 1515.0
    assert body["discount_percent"] == 0
    assert body["discount"] == 0
    assert body["taxable_amount"] == 1515.0
    assert body["tax_rate"] == 21
    assert body["tax"] == 318.15
    assert body["total"] == 1833.15
    assert body["currency"] == "USD"


def test_header_fields(client, api_key_headers):
    order = client.get(f"/orders/{ORDER_ID}", headers=api_key_headers).json()
    body = _invoice(client, api_key_headers).json()
    assert body["order_id"] == ORDER_ID
    assert body["order_number"] == order["order_number"]
    assert body["invoice_number"] == order["order_number"].replace("ORD-", "INV-", 1)
    assert body["issued_on"] == order["created_at"][:10]
    assert body["customer"]["name"] == order["customer_name"]


def test_lines(client, api_key_headers):
    lines = _invoice(client, api_key_headers).json()["lines"]
    assert lines == [
        {"sku": "SAIL-MAIN-052", "description": "Mainsail Dacron 5.2m", "quantity": 2,
         "unit_price": 720.0, "amount": 1440.0},
        {"sku": "HW-SHK-08", "description": "Stainless Shackle 8mm", "quantity": 10,
         "unit_price": 7.5, "amount": 75.0},
    ]


def test_discount_applies_before_tax(client, api_key_headers):
    body = _invoice(client, api_key_headers, query="?discount_percent=10&tax_rate=10").json()
    assert body["discount"] == 151.5
    assert body["taxable_amount"] == 1363.5
    assert body["tax"] == 136.35
    assert body["total"] == 1499.85


def test_each_step_is_rounded_to_cents(client, api_key_headers):
    body = _invoice(client, api_key_headers, query="?discount_percent=3.33&tax_rate=7.5").json()
    assert body["discount"] == 50.45     # 50.4495
    assert body["taxable_amount"] == 1464.55
    assert body["tax"] == 109.84         # 109.84125
    assert body["total"] == 1574.39


def test_full_discount_and_no_tax(client, api_key_headers):
    assert _invoice(client, api_key_headers, query="?discount_percent=100").json()["total"] == 0
    assert _invoice(client, api_key_headers, query="?tax_rate=0").json()["total"] == 1515.0


def test_out_of_range_parameters(client, api_key_headers):
    for query in ("?tax_rate=-1", "?tax_rate=30.01", "?discount_percent=-0.5",
                  "?discount_percent=101", "?tax_rate=abc"):
        assert _invoice(client, api_key_headers, query=query).status_code == 422, query
    assert _invoice(client, api_key_headers, query="?tax_rate=30").status_code == 200


def test_reflects_edited_items(client, api_key_headers):
    client.put(f"/orders/{ORDER_ID}/items", headers=api_key_headers,
               json={"items": [{"sku": "HW-SHK-08", "quantity": 4}]})
    body = _invoice(client, api_key_headers, query="?tax_rate=0").json()
    assert body["subtotal"] == 30.0
    assert len(body["lines"]) == 1


def test_cancelled_order_has_no_invoice(client, api_key_headers):
    client.patch(f"/orders/{ORDER_ID}/status", headers=api_key_headers,
                 json={"status": "cancelled"})
    res = _invoice(client, api_key_headers)
    assert res.status_code == 409
    assert res.json()["detail"] == "Cancelled orders have no invoice"


def test_pending_order_has_an_invoice(client, api_key_headers):
    client.patch(f"/orders/{ORDER_ID}/status", headers=api_key_headers,
                 json={"status": "pending"})
    assert _invoice(client, api_key_headers).status_code == 200


def test_unknown_order(client, api_key_headers):
    res = _invoice(client, api_key_headers, order_id=9999)
    assert res.status_code == 404
    assert res.json()["detail"] == "Order not found"
