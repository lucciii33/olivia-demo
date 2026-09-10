"""POST /products/bulk-adjust — adjust several products at once, all or nothing."""

# Seed quantities after the two demo orders (see db.py):
#   ACC-TAPE-01   3  (minimum 10, low stock)
#   LINE-DYN-06  60  (minimum 100, low stock)
#   HW-SHK-08   230
#   SAIL-SPIN-15  5
TAPE, DYNEEMA, SHACKLE, SPINNAKER = "ACC-TAPE-01", "LINE-DYN-06", "HW-SHK-08", "SAIL-SPIN-15"


def _qty(client, headers, sku):
    items = client.get(f"/products?q={sku}", headers=headers).json()["items"]
    [product] = [p for p in items if p["sku"] == sku]
    return product["quantity"]


def _bulk(client, headers, items, **extra):
    return client.post("/products/bulk-adjust", headers=headers, json={"items": items, **extra})


def test_requires_auth(client):
    res = client.post("/products/bulk-adjust", json={"items": [{"sku": TAPE, "delta": 1}]})
    assert res.status_code == 401


def test_adjusts_several_products(client, api_key_headers):
    res = _bulk(client, api_key_headers, [
        {"sku": TAPE, "delta": 20},
        {"sku": DYNEEMA, "delta": 50},
        {"sku": SHACKLE, "delta": -30},
    ])
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 3
    by_sku = {a["sku"]: a for a in body["adjusted"]}
    assert by_sku[TAPE]["previous_quantity"] == 3
    assert by_sku[TAPE]["delta"] == 20
    assert by_sku[TAPE]["quantity"] == 23
    assert by_sku[DYNEEMA]["quantity"] == 110
    assert by_sku[SHACKLE]["quantity"] == 200

    # Persisted, not just echoed back.
    assert _qty(client, api_key_headers, TAPE) == 23
    assert _qty(client, api_key_headers, DYNEEMA) == 110
    assert _qty(client, api_key_headers, SHACKLE) == 200


def test_restock_clears_low_stock(client, api_key_headers):
    assert client.get("/products/low-stock", headers=api_key_headers).json()["count"] == 2
    body = _bulk(client, api_key_headers, [{"sku": TAPE, "delta": 20},
                                           {"sku": DYNEEMA, "delta": 50}]).json()
    assert all(a["low_stock"] is False for a in body["adjusted"])
    assert client.get("/products/low-stock", headers=api_key_headers).json()["count"] == 0


def test_reason_is_echoed(client, api_key_headers):
    body = _bulk(client, api_key_headers, [{"sku": TAPE, "delta": 1}],
                 reason="inventario fisico").json()
    assert body["reason"] == "inventario fisico"


def test_insufficient_stock_changes_nothing(client, api_key_headers):
    res = _bulk(client, api_key_headers, [
        {"sku": TAPE, "delta": 5},        # valid on its own
        {"sku": SPINNAKER, "delta": -6},  # only 5 in stock
    ])
    assert res.status_code == 400
    assert SPINNAKER in res.json()["detail"]
    assert _qty(client, api_key_headers, TAPE) == 3
    assert _qty(client, api_key_headers, SPINNAKER) == 5


def test_unknown_sku_changes_nothing(client, api_key_headers):
    res = _bulk(client, api_key_headers, [{"sku": TAPE, "delta": 5},
                                          {"sku": "NO-EXISTE", "delta": 1}])
    assert res.status_code == 400
    assert "NO-EXISTE" in res.json()["detail"]
    assert _qty(client, api_key_headers, TAPE) == 3


def test_repeated_sku_is_rejected(client, api_key_headers):
    res = _bulk(client, api_key_headers, [{"sku": TAPE, "delta": 5},
                                          {"sku": TAPE, "delta": -1}])
    assert res.status_code == 400
    assert TAPE in res.json()["detail"]
    assert _qty(client, api_key_headers, TAPE) == 3


def test_empty_list_is_422(client, api_key_headers):
    assert _bulk(client, api_key_headers, []).status_code == 422


def test_more_than_100_items_is_422(client, api_key_headers):
    items = [{"sku": f"SKU-{i}", "delta": 1} for i in range(101)]
    assert _bulk(client, api_key_headers, items).status_code == 422


def test_single_product_routes_still_work(client, api_key_headers):
    # /products/bulk-adjust must not shadow, or be shadowed by, /products/{id}.
    assert client.get("/products/1", headers=api_key_headers).status_code == 200
    res = client.post("/products/7/adjust-stock", headers=api_key_headers, json={"delta": 1})
    assert res.status_code == 200
    assert res.json()["product"]["quantity"] == 4
