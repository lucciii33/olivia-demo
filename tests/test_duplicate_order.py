"""POST /orders/{id}/duplicate — the same order again, as a new one at today's prices."""

ORDER_ID = 1  # seed: SAIL-MAIN-052 x2 @ 720.0 and HW-SHK-08 x10 @ 7.5 (total 1515.0)


def _dup(client, headers, order_id=ORDER_ID, json=None):
    return client.post(f"/orders/{order_id}/duplicate", headers=headers, json=json)


def _stock(client, headers, sku):
    return client.get(f"/products/by-sku/{sku}", headers=headers).json()["quantity"]


def test_requires_auth(client):
    assert client.post(f"/orders/{ORDER_ID}/duplicate").status_code == 401


def test_creates_a_new_accepted_order(client, api_key_headers):
    source = client.get(f"/orders/{ORDER_ID}", headers=api_key_headers).json()
    res = _dup(client, api_key_headers)
    assert res.status_code == 201
    body = res.json()
    assert body["id"] != ORDER_ID
    assert body["order_number"] != source["order_number"]
    assert body["duplicated_from"] == source["order_number"]
    assert body["status"] == "accepted"
    assert body["customer_name"] == source["customer_name"]
    assert body["total"] == 1515.0
    assert [(i["product_name"], i["quantity"]) for i in body["items"]] == \
        [(i["product_name"], i["quantity"]) for i in source["items"]]


def test_takes_stock_and_leaves_the_source_alone(client, api_key_headers):
    _dup(client, api_key_headers)
    assert _stock(client, api_key_headers, "SAIL-MAIN-052") == 8
    assert _stock(client, api_key_headers, "HW-SHK-08") == 220
    source = client.get(f"/orders/{ORDER_ID}", headers=api_key_headers).json()
    assert source["total"] == 1515.0
    assert client.get("/orders", headers=api_key_headers).json()["total_count"] == 3


def test_uses_current_prices(client, api_key_headers):
    client.put("/products/1", headers=api_key_headers, json={"sale_price": 800.0})
    body = _dup(client, api_key_headers).json()
    mainsail = next(i for i in body["items"] if i["product_name"] == "Mainsail Dacron 5.2m")
    assert mainsail["unit_price"] == 800.0
    assert body["total"] == 1675.0  # 2 x 800 + 10 x 7.5


def test_customer_name_and_notes_can_be_overridden(client, api_key_headers):
    body = _dup(client, api_key_headers,
                json={"customer_name": "Otro Cliente", "notes": "Repetir urgente"}).json()
    assert body["customer_name"] == "Otro Cliente"
    assert body["notes"] == "Repetir urgente"


def test_empty_notes_clears_them(client, api_key_headers):
    assert _dup(client, api_key_headers, json={"notes": ""}).json()["notes"] == ""


def test_cancelled_orders_can_be_duplicated(client, api_key_headers):
    client.patch(f"/orders/{ORDER_ID}/status", headers=api_key_headers,
                 json={"status": "cancelled"})
    body = _dup(client, api_key_headers).json()
    assert body["status"] == "accepted"
    assert _stock(client, api_key_headers, "SAIL-MAIN-052") == 10  # 12 after cancel, minus 2


def test_not_enough_stock_creates_nothing(client, api_key_headers):
    for _ in range(5):  # 10 mainsails left, 2 per copy
        assert _dup(client, api_key_headers).status_code == 201
    res = _dup(client, api_key_headers)
    assert res.status_code == 409
    assert res.json()["detail"] == "Not enough stock for SAIL-MAIN-052: have 0, need 2"
    assert client.get("/orders", headers=api_key_headers).json()["total_count"] == 7
    assert _stock(client, api_key_headers, "HW-SHK-08") == 180


def test_unknown_order(client, api_key_headers):
    res = _dup(client, api_key_headers, order_id=9999)
    assert res.status_code == 404
    assert res.json()["detail"] == "Order not found"
