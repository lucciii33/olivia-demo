"""GET /stats/top-products — limit bounds, sort_by, orders and revenue_share."""

SEED_REVENUE = 2349.0
BY_UNITS = ["HW-SHK-08", "ACC-TELL-01", "SAIL-MAIN-052", "SAIL-GEN-135"]
BY_REVENUE = ["SAIL-MAIN-052", "SAIL-GEN-135", "HW-SHK-08", "ACC-TELL-01"]


def _top(client, headers, **params):
    return client.get("/stats/top-products", headers=headers, params=params)


def test_requires_auth(client):
    assert client.get("/stats/top-products").status_code == 401


def test_default_sorts_by_units_sold(client, api_key_headers):
    body = _top(client, api_key_headers).json()
    assert body["sort_by"] == "units_sold"
    assert body["count"] == 4
    assert [i["sku"] for i in body["items"]] == BY_UNITS


def test_sort_by_revenue(client, api_key_headers):
    body = _top(client, api_key_headers, sort_by="revenue").json()
    assert body["sort_by"] == "revenue"
    assert [i["sku"] for i in body["items"]] == BY_REVENUE


def test_unknown_sort_by_is_rejected(client, api_key_headers):
    assert _top(client, api_key_headers, sort_by="name").status_code == 422


def test_limit_cuts_the_list(client, api_key_headers):
    body = _top(client, api_key_headers, limit=2, sort_by="revenue").json()
    assert body["count"] == 2
    assert [i["sku"] for i in body["items"]] == BY_REVENUE[:2]


def test_limit_bounds(client, api_key_headers):
    assert _top(client, api_key_headers, limit=0).status_code == 422
    assert _top(client, api_key_headers, limit=51).status_code == 422
    assert _top(client, api_key_headers, limit=50).status_code == 200


def test_total_revenue_and_shares(client, api_key_headers):
    body = _top(client, api_key_headers).json()
    assert body["total_revenue"] == SEED_REVENUE
    assert body["currency"] == "USD"
    mainsail = next(i for i in body["items"] if i["sku"] == "SAIL-MAIN-052")
    assert mainsail["revenue"] == 1440.0
    assert mainsail["revenue_share"] == 61.3
    # All products are listed, so the shares add up to (about) 100%.
    assert abs(sum(i["revenue_share"] for i in body["items"]) - 100) < 0.05


def test_total_revenue_ignores_limit(client, api_key_headers):
    assert _top(client, api_key_headers, limit=1).json()["total_revenue"] == SEED_REVENUE


def test_orders_counts_distinct_orders(client, api_key_headers):
    for quantity in (1, 2):
        client.post("/orders", headers=api_key_headers, json={
            "customer_name": "Astillero Norte",
            "items": [{"sku": "HW-SHK-08", "quantity": quantity}],
        })
    shackle = _top(client, api_key_headers).json()["items"][0]
    assert shackle["sku"] == "HW-SHK-08"
    assert shackle["orders"] == 3
    assert shackle["units_sold"] == 13


def test_cancelled_orders_do_not_count(client, api_key_headers):
    order = client.post("/orders", headers=api_key_headers, json={
        "customer_name": "Astillero Norte",
        "items": [{"sku": "HW-SHK-08", "quantity": 5}],
    }).json()
    client.patch(f"/orders/{order['id']}/status", headers=api_key_headers,
                 json={"status": "cancelled"})
    body = _top(client, api_key_headers).json()
    assert body["total_revenue"] == SEED_REVENUE
    assert body["items"][0]["units_sold"] == 10
