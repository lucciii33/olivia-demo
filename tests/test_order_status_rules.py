"""PATCH /orders/{id}/status — previous_status, and cancelling is final."""

ORDER_ID = 1  # seed: accepted, SAIL-MAIN-052 x2 and HW-SHK-08 x10


def _set(client, headers, status, order_id=ORDER_ID):
    return client.patch(f"/orders/{order_id}/status", headers=headers, json={"status": status})


def _stock(client, headers, sku):
    return client.get(f"/products/by-sku/{sku}", headers=headers).json()["quantity"]


def test_response_includes_previous_status(client, api_key_headers):
    body = _set(client, api_key_headers, "pending").json()
    assert body["status"] == "pending"
    assert body["previous_status"] == "accepted"


def test_same_status_is_allowed(client, api_key_headers):
    body = _set(client, api_key_headers, "accepted").json()
    assert body["previous_status"] == "accepted"


def test_cancelled_order_cannot_change_status(client, api_key_headers):
    _set(client, api_key_headers, "cancelled")
    for status in ("pending", "accepted", "cancelled"):
        res = _set(client, api_key_headers, status)
        assert res.status_code == 409, status
        assert res.json()["detail"] == "Cancelled orders cannot change status"
    order = client.get(f"/orders/{ORDER_ID}", headers=api_key_headers).json()
    assert order["status"] == "cancelled"


def test_cancelling_restocks_exactly_once(client, api_key_headers):
    _set(client, api_key_headers, "cancelled")
    _set(client, api_key_headers, "cancelled")  # refused, so no second restock
    assert _stock(client, api_key_headers, "HW-SHK-08") == 240


def test_pending_order_can_still_be_cancelled(client, api_key_headers):
    _set(client, api_key_headers, "pending")
    body = _set(client, api_key_headers, "cancelled").json()
    assert body["previous_status"] == "pending"
    assert _stock(client, api_key_headers, "HW-SHK-08") == 240


def test_invalid_status_and_unknown_order(client, api_key_headers):
    assert _set(client, api_key_headers, "shipped").status_code == 400
    assert _set(client, api_key_headers, "accepted", order_id=9999).status_code == 404
