"""GET /stats/top-customers — revenue per customer, cancelled orders excluded."""

# Seed orders: Blue Marina SL 1515.0 and Regatta Club 834.0, both accepted.
BLUE, REGATTA = "Blue Marina SL", "Regatta Club"
REGATTA_EMAIL = "info@regatta.example"
SEED_REVENUE = 2349.0


def _top(client, headers):
    return client.get("/stats/top-customers", headers=headers)


def _order(client, headers, customer, quantity=1, email=None, sku="HW-WIN-10"):
    # HW-WIN-10 sells at 49.0, SAIL-MAIN-052 at 720.0
    return client.post("/orders", headers=headers, json={
        "customer_name": customer,
        "customer_email": email,
        "items": [{"sku": sku, "quantity": quantity}],
    }).json()


def test_requires_auth(client):
    assert client.get("/stats/top-customers").status_code == 401


def test_needs_no_parameters(client, api_key_headers):
    assert _top(client, api_key_headers).status_code == 200


def test_seed_ranking(client, api_key_headers):
    body = _top(client, api_key_headers).json()
    assert body["count"] == 2
    assert body["revenue"] == SEED_REVENUE
    assert body["currency"] == "USD"
    assert [(i["customer_name"], i["orders"], i["revenue"]) for i in body["items"]] == [
        (BLUE, 1, 1515.0),
        (REGATTA, 1, 834.0),
    ]


def test_matches_overview_revenue(client, api_key_headers):
    revenue = client.get("/stats/overview", headers=api_key_headers).json()["revenue"]
    assert _top(client, api_key_headers).json()["revenue"] == revenue


def test_cancelled_orders_are_excluded(client, api_key_headers):
    order = _order(client, api_key_headers, "Astillero Norte", quantity=4)
    assert "Astillero Norte" in [i["customer_name"] for i in _top(client, api_key_headers).json()["items"]]

    client.patch(f"/orders/{order['id']}/status", headers=api_key_headers,
                 json={"status": "cancelled"})
    body = _top(client, api_key_headers).json()
    assert "Astillero Norte" not in [i["customer_name"] for i in body["items"]]
    assert body["revenue"] == SEED_REVENUE


def test_several_orders_from_one_customer_add_up(client, api_key_headers):
    _order(client, api_key_headers, REGATTA, quantity=2, email=REGATTA_EMAIL)  # 98.0
    [regatta] = [i for i in _top(client, api_key_headers).json()["items"]
                 if i["customer_email"] == REGATTA_EMAIL]
    assert regatta == {"customer_name": REGATTA, "customer_email": REGATTA_EMAIL,
                       "orders": 2, "revenue": 932.0}


def test_same_name_with_another_email_is_a_separate_row(client, api_key_headers):
    # Rows are grouped by name and email together, like the orders themselves.
    _order(client, api_key_headers, REGATTA, quantity=1, email="compras@regatta.example")
    rows = [i for i in _top(client, api_key_headers).json()["items"]
            if i["customer_name"] == REGATTA]
    assert sorted(i["customer_email"] for i in rows) == ["compras@regatta.example", REGATTA_EMAIL]


def test_a_big_order_takes_the_top_spot(client, api_key_headers):
    # 3 mainsails at 720.0 = 2160.0, above Blue Marina's 1515.0.
    _order(client, api_key_headers, "Astillero Norte", quantity=3, sku="SAIL-MAIN-052")
    body = _top(client, api_key_headers).json()
    assert [i["customer_name"] for i in body["items"]][:2] == ["Astillero Norte", BLUE]
    assert body["items"][0]["revenue"] == 2160.0
