"""PUT /orders/{id}/items — replace an order's lines, moving stock and the total."""

# Seed order 1: SAIL-MAIN-052 x2 @ 720.0 and HW-SHK-08 x10 @ 7.5 (total 1515.0).
ORDER_ID = 1
STOCK = {"SAIL-MAIN-052": 10, "HW-SHK-08": 230, "SAIL-SPIN-15": 5, "HW-WIN-10": 18}


def _put(client, headers, items, order_id=ORDER_ID):
    return client.put(f"/orders/{order_id}/items", headers=headers, json={"items": items})


def _stock(client, headers, sku):
    return client.get(f"/products/by-sku/{sku}", headers=headers).json()["quantity"]


def _lines(body):
    return {(i["product_name"], i["quantity"], i["unit_price"]) for i in body["items"]}


def _seed_items():
    return [{"sku": "SAIL-MAIN-052", "quantity": 2}, {"sku": "HW-SHK-08", "quantity": 10}]


def test_requires_auth(client):
    assert client.put(f"/orders/{ORDER_ID}/items", json={"items": _seed_items()}).status_code == 401


def test_same_items_change_nothing(client, api_key_headers):
    body = _put(client, api_key_headers, _seed_items()).json()
    assert body["total"] == 1515.0
    assert body["changes"] == []
    assert _stock(client, api_key_headers, "SAIL-MAIN-052") == STOCK["SAIL-MAIN-052"]


def test_raising_a_quantity_takes_stock(client, api_key_headers):
    body = _put(client, api_key_headers, [{"sku": "SAIL-MAIN-052", "quantity": 3},
                                          {"sku": "HW-SHK-08", "quantity": 10}]).json()
    assert body["total"] == 2235.0
    assert body["changes"] == [
        {"sku": "SAIL-MAIN-052", "before": 2, "after": 3, "stock_delta": -1}]
    assert _stock(client, api_key_headers, "SAIL-MAIN-052") == 9


def test_lowering_a_quantity_returns_stock(client, api_key_headers):
    body = _put(client, api_key_headers, [{"sku": "SAIL-MAIN-052", "quantity": 2},
                                          {"sku": "HW-SHK-08", "quantity": 4}]).json()
    assert body["total"] == 1470.0
    assert body["changes"] == [{"sku": "HW-SHK-08", "before": 10, "after": 4, "stock_delta": 6}]
    assert _stock(client, api_key_headers, "HW-SHK-08") == 236


def test_dropped_line_is_restocked_and_new_line_takes_stock(client, api_key_headers):
    body = _put(client, api_key_headers, [{"sku": "SAIL-MAIN-052", "quantity": 2},
                                          {"sku": "HW-WIN-10", "quantity": 3}]).json()
    assert body["total"] == 1587.0  # 2 x 720 + 3 x 49
    assert body["changes"] == [
        {"sku": "HW-WIN-10", "before": 0, "after": 3, "stock_delta": -3},
        {"sku": "HW-SHK-08", "before": 10, "after": 0, "stock_delta": 10},
    ]
    assert _stock(client, api_key_headers, "HW-WIN-10") == 15
    assert _stock(client, api_key_headers, "HW-SHK-08") == 240


def test_kept_lines_keep_their_sold_price(client, api_key_headers):
    client.put("/products/1", headers=api_key_headers, json={"sale_price": 999.0})  # mainsail
    client.put("/products/6", headers=api_key_headers, json={"sale_price": 50.0})  # winch handle
    body = _put(client, api_key_headers, [{"sku": "SAIL-MAIN-052", "quantity": 1},
                                          {"sku": "HW-WIN-10", "quantity": 1}]).json()
    assert _lines(body) == {("Mainsail Dacron 5.2m", 1, 720.0), ("Winch Handle 10in", 1, 50.0)}
    assert body["total"] == 770.0


def test_order_fields_are_kept(client, api_key_headers):
    before = client.get(f"/orders/{ORDER_ID}", headers=api_key_headers).json()
    body = _put(client, api_key_headers, [{"sku": "HW-SHK-08", "quantity": 1}]).json()
    for field in ("order_number", "customer_name", "status", "created_at"):
        assert body[field] == before[field]
    assert body["updated_at"] >= before["updated_at"]


def test_the_change_is_saved(client, api_key_headers):
    _put(client, api_key_headers, [{"sku": "HW-SHK-08", "quantity": 1}])
    order = client.get(f"/orders/{ORDER_ID}", headers=api_key_headers).json()
    assert order["total"] == 7.5
    assert order["items_count"] == 1


def test_not_enough_stock_changes_nothing(client, api_key_headers):
    # 9 more mainsails are needed on top of the 2 already held, with 10 left: fine.
    assert _put(client, api_key_headers, [{"sku": "SAIL-MAIN-052", "quantity": 12}]).status_code == 200
    # Back to the seed, then ask for one more than the stock can cover.
    _put(client, api_key_headers, _seed_items())
    res = _put(client, api_key_headers, [{"sku": "HW-SHK-08", "quantity": 1},
                                         {"sku": "SAIL-MAIN-052", "quantity": 13}])
    assert res.status_code == 409
    assert res.json()["detail"] == "Not enough stock for SAIL-MAIN-052: have 10, need 11"
    order = client.get(f"/orders/{ORDER_ID}", headers=api_key_headers).json()
    assert order["total"] == 1515.0
    assert _stock(client, api_key_headers, "HW-SHK-08") == STOCK["HW-SHK-08"]


def test_unknown_sku_changes_nothing(client, api_key_headers):
    res = _put(client, api_key_headers, [{"sku": "HW-SHK-08", "quantity": 1},
                                         {"sku": "NOPE-1", "quantity": 1}])
    assert res.status_code == 400
    assert res.json()["detail"] == "Unknown SKU 'NOPE-1'"
    assert _stock(client, api_key_headers, "HW-SHK-08") == STOCK["HW-SHK-08"]


def test_duplicate_sku_is_rejected(client, api_key_headers):
    res = _put(client, api_key_headers, [{"sku": "HW-SHK-08", "quantity": 1},
                                         {"sku": "HW-SHK-08", "quantity": 2}])
    assert res.status_code == 400
    assert res.json()["detail"] == "Duplicate SKU 'HW-SHK-08'"


def test_body_validation(client, api_key_headers):
    assert _put(client, api_key_headers, []).status_code == 422
    assert _put(client, api_key_headers, [{"sku": "HW-SHK-08", "quantity": 0}]).status_code == 422
    many = [{"sku": f"X-{n}", "quantity": 1} for n in range(51)]
    assert _put(client, api_key_headers, many).status_code == 422


def test_unknown_order(client, api_key_headers):
    res = _put(client, api_key_headers, _seed_items(), order_id=9999)
    assert res.status_code == 404


def test_cancelled_order_cannot_be_edited(client, api_key_headers):
    client.patch(f"/orders/{ORDER_ID}/status", headers=api_key_headers,
                 json={"status": "cancelled"})
    res = _put(client, api_key_headers, _seed_items())
    assert res.status_code == 409
    assert res.json()["detail"] == "Cancelled orders cannot be edited"
