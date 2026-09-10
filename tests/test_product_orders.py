"""GET /products/{product_id}/orders — sales history of one product."""
import auth

# From the seed in db.py: order ORD-...-0001 (Blue Marina SL) sold 2 units of
# product 1 at 720.0; product 3 (the spinnaker) was never ordered.
MAINSAIL_ID = 1
SPINNAKER_ID = 3
WINCH_SKU = "HW-WIN-10"
WINCH_ID = 6


def test_requires_auth(client):
    assert client.get(f"/products/{MAINSAIL_ID}/orders").status_code == 401


def test_accepts_bearer_token(client):
    headers = {"Authorization": f"Bearer {auth.BEARER_TOKEN}"}
    assert client.get(f"/products/{MAINSAIL_ID}/orders", headers=headers).status_code == 200


def test_history_of_seeded_product(client, api_key_headers):
    res = client.get(f"/products/{MAINSAIL_ID}/orders", headers=api_key_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["product"]["id"] == MAINSAIL_ID
    assert body["orders_count"] == 1
    assert body["units_sold"] == 2
    assert body["revenue"] == 1440.0
    [item] = body["items"]
    assert item["order_number"].endswith("-0001")
    assert item["customer_name"] == "Blue Marina SL"
    assert item["quantity"] == 2
    assert item["unit_price"] == 720.0


def test_product_never_ordered(client, api_key_headers):
    body = client.get(f"/products/{SPINNAKER_ID}/orders", headers=api_key_headers).json()
    assert body["orders_count"] == 0
    assert body["units_sold"] == 0
    assert body["revenue"] == 0
    assert body["items"] == []


def test_unknown_product_is_404(client, api_key_headers):
    assert client.get("/products/999/orders", headers=api_key_headers).status_code == 404


def test_non_integer_id_is_422(client, api_key_headers):
    assert client.get("/products/abc/orders", headers=api_key_headers).status_code == 422


def test_new_orders_show_up(client, api_key_headers):
    order = client.post("/orders", headers=api_key_headers, json={
        "customer_name": "Astillero Norte",
        "items": [{"sku": WINCH_SKU, "quantity": 3}],
    }).json()

    body = client.get(f"/products/{WINCH_ID}/orders", headers=api_key_headers).json()
    assert body["orders_count"] == 1
    assert body["units_sold"] == 3
    assert body["items"][0]["order_id"] == order["id"]


def test_cancelled_orders_hidden_unless_requested(client, api_key_headers):
    order = client.post("/orders", headers=api_key_headers, json={
        "customer_name": "Astillero Norte",
        "items": [{"sku": WINCH_SKU, "quantity": 2}],
    }).json()
    client.patch(f"/orders/{order['id']}/status", headers=api_key_headers,
                 json={"status": "cancelled"})

    default = client.get(f"/products/{WINCH_ID}/orders", headers=api_key_headers).json()
    assert default["orders_count"] == 0
    assert default["revenue"] == 0

    everything = client.get(f"/products/{WINCH_ID}/orders?include_cancelled=true",
                            headers=api_key_headers).json()
    assert everything["orders_count"] == 1
    assert everything["items"][0]["status"] == "cancelled"


def test_newest_orders_first(client, api_key_headers):
    for name in ("Primero", "Segundo"):
        client.post("/orders", headers=api_key_headers, json={
            "customer_name": name,
            "items": [{"sku": WINCH_SKU, "quantity": 1}],
        })
    items = client.get(f"/products/{WINCH_ID}/orders", headers=api_key_headers).json()["items"]
    assert [i["customer_name"] for i in items] == ["Segundo", "Primero"]
