"""GET /orders/{id}/invoice — shipping and instalments."""

# Seed order 1: subtotal 1515.0, so shipping is free.
ORDER_ID = 1


def _invoice(client, headers, order_id=ORDER_ID, **params):
    return client.get(f"/orders/{order_id}/invoice", headers=headers, params=params)


def _small_order(client, headers):
    # HW-WIN-10 sells at 49.0
    return client.post("/orders", headers=headers, json={
        "customer_name": "Astillero Norte",
        "items": [{"sku": "HW-WIN-10", "quantity": 2}],
    }).json()["id"]


def test_free_shipping_from_1000(client, api_key_headers):
    body = _invoice(client, api_key_headers).json()
    assert body["shipping"] == 0.0
    assert body["total"] == 1833.15
    assert body["instalments"] == 1
    assert body["instalment_amount"] == 1833.15


def test_small_order_pays_shipping_untaxed(client, api_key_headers):
    order_id = _small_order(client, api_key_headers)
    body = _invoice(client, api_key_headers, order_id=order_id).json()
    assert body["taxable_amount"] == 98.0
    assert body["tax"] == 20.58
    assert body["shipping"] == 25.0
    assert body["total"] == 143.58


def test_instalments_split_the_total(client, api_key_headers):
    body = _invoice(client, api_key_headers, instalments=3).json()
    assert body["instalments"] == 3
    assert body["instalment_amount"] == 611.05


def test_converted_total_includes_shipping(client, api_key_headers):
    order_id = _small_order(client, api_key_headers)
    body = _invoice(client, api_key_headers, order_id=order_id, currency="EUR").json()
    assert body["converted_total"] == round(143.58 * 0.92, 2)


def test_too_many_instalments(client, api_key_headers):
    assert _invoice(client, api_key_headers, instalments=13).status_code == 422
