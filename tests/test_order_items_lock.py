"""PUT /orders/{id}/items — expected_total lock and ?dry_run."""

ORDER_ID = 1  # seed: SAIL-MAIN-052 x2 @ 720.0 + HW-SHK-08 x10 @ 7.5, total 1515.0


def _put(client, headers, body, query=""):
    return client.put(f"/orders/{ORDER_ID}/items{query}", headers=headers, json=body)


def _order(client, headers):
    return client.get(f"/orders/{ORDER_ID}", headers=headers).json()


def _stock(client, headers, sku):
    return client.get(f"/products/by-sku/{sku}", headers=headers).json()["quantity"]


ONE_SHACKLE = [{"sku": "HW-SHK-08", "quantity": 1}]


def test_matching_expected_total_applies(client, api_key_headers):
    res = _put(client, api_key_headers, {"items": ONE_SHACKLE, "expected_total": 1515})
    assert res.status_code == 200
    assert res.json()["total"] == 7.5
    assert res.json()["dry_run"] is False


def test_stale_expected_total_is_409(client, api_key_headers):
    res = _put(client, api_key_headers, {"items": ONE_SHACKLE, "expected_total": 1500})
    assert res.status_code == 409
    assert res.json()["detail"] == "Order changed: expected total 1500.0, current 1515.0"
    assert _order(client, api_key_headers)["total"] == 1515.0


def test_expected_total_is_compared_in_cents(client, api_key_headers):
    res = _put(client, api_key_headers, {"items": ONE_SHACKLE, "expected_total": 1515.001})
    assert res.status_code == 200


def test_negative_expected_total_is_422(client, api_key_headers):
    assert _put(client, api_key_headers,
                {"items": ONE_SHACKLE, "expected_total": -1}).status_code == 422


def test_lock_is_checked_after_cancelled(client, api_key_headers):
    client.patch(f"/orders/{ORDER_ID}/status", headers=api_key_headers,
                 json={"status": "cancelled"})
    res = _put(client, api_key_headers, {"items": ONE_SHACKLE, "expected_total": 1})
    assert res.json()["detail"] == "Cancelled orders cannot be edited"


def test_lock_is_checked_before_unknown_sku(client, api_key_headers):
    res = _put(client, api_key_headers,
               {"items": [{"sku": "NOPE", "quantity": 1}], "expected_total": 1})
    assert res.status_code == 409
    assert res.json()["detail"].startswith("Order changed")


def test_dry_run_previews_without_saving(client, api_key_headers):
    res = _put(client, api_key_headers, {"items": ONE_SHACKLE}, "?dry_run=true")
    assert res.status_code == 200
    body = res.json()
    assert body["dry_run"] is True
    assert body["total"] == 7.5
    assert len(body["items"]) == 1
    assert {c["sku"] for c in body["changes"]} == {"HW-SHK-08", "SAIL-MAIN-052"}
    order = _order(client, api_key_headers)
    assert order["total"] == 1515.0
    assert order["items_count"] == 2
    assert _stock(client, api_key_headers, "SAIL-MAIN-052") == 10
    assert _stock(client, api_key_headers, "HW-SHK-08") == 230


def test_dry_run_still_validates(client, api_key_headers):
    res = _put(client, api_key_headers,
               {"items": [{"sku": "SAIL-MAIN-052", "quantity": 13}]}, "?dry_run=true")
    assert res.status_code == 409
    assert res.json()["detail"] == "Not enough stock for SAIL-MAIN-052: have 10, need 11"


def test_dry_run_with_lock(client, api_key_headers):
    ok = _put(client, api_key_headers, {"items": ONE_SHACKLE, "expected_total": 1515},
              "?dry_run=true")
    assert ok.status_code == 200
    stale = _put(client, api_key_headers, {"items": ONE_SHACKLE, "expected_total": 7.5},
                 "?dry_run=true")
    assert stale.status_code == 409
