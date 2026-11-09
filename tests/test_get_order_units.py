"""GET /orders/{id} — units_count and editable."""

ORDER_ID = 2  # seed: SAIL-GEN-135 x1 + ACC-TELL-01 x4, accepted


def _get(client, headers, query="", order_id=ORDER_ID):
    return client.get(f"/orders/{order_id}{query}", headers=headers)


def test_units_count_adds_up_quantities(client, api_key_headers):
    body = _get(client, api_key_headers).json()
    assert body["items_count"] == 2
    assert body["units_count"] == 5


def test_accepted_and_pending_orders_are_editable(client, api_key_headers):
    assert _get(client, api_key_headers).json()["editable"] is True
    client.patch(f"/orders/{ORDER_ID}/status", headers=api_key_headers, json={"status": "pending"})
    assert _get(client, api_key_headers).json()["editable"] is True


def test_cancelled_order_is_not_editable(client, api_key_headers):
    client.patch(f"/orders/{ORDER_ID}/status", headers=api_key_headers,
                 json={"status": "cancelled"})
    body = _get(client, api_key_headers).json()
    assert body["editable"] is False
    assert body["units_count"] == 5


def test_fields_stay_without_items(client, api_key_headers):
    body = _get(client, api_key_headers, "?include_items=false").json()
    assert "items" not in body
    assert body["units_count"] == 5
    assert body["editable"] is True


def test_units_count_follows_item_edits(client, api_key_headers):
    client.put(f"/orders/{ORDER_ID}/items", headers=api_key_headers,
               json={"items": [{"sku": "ACC-TELL-01", "quantity": 7}]})
    assert _get(client, api_key_headers).json()["units_count"] == 7


def test_unknown_order(client, api_key_headers):
    assert _get(client, api_key_headers, order_id=9999).status_code == 404
