"""GET /orders/{order_id} — items_count, include_items, no inventory_deducted."""

# Seed order 1 (Blue Marina SL): 2 mainsails + 10 shackles, two line items.
ORDER_ID = 1


def test_requires_auth(client):
    assert client.get(f"/orders/{ORDER_ID}").status_code == 401


def test_returns_items_count(client, api_key_headers):
    body = client.get(f"/orders/{ORDER_ID}", headers=api_key_headers).json()
    assert body["items_count"] == 2
    assert len(body["items"]) == 2


def test_inventory_deducted_is_gone(client, api_key_headers):
    body = client.get(f"/orders/{ORDER_ID}", headers=api_key_headers).json()
    assert "inventory_deducted" not in body


def test_include_items_false_omits_items(client, api_key_headers):
    body = client.get(f"/orders/{ORDER_ID}?include_items=false", headers=api_key_headers).json()
    assert "items" not in body
    assert body["items_count"] == 2
    assert body["order_number"].endswith("-0001")


def test_include_items_true_is_the_default(client, api_key_headers):
    explicit = client.get(f"/orders/{ORDER_ID}?include_items=true", headers=api_key_headers).json()
    default = client.get(f"/orders/{ORDER_ID}", headers=api_key_headers).json()
    assert explicit == default


def test_unknown_order_is_404(client, api_key_headers):
    assert client.get("/orders/999", headers=api_key_headers).status_code == 404


def test_other_order_responses_keep_their_shape(client, api_key_headers):
    # POST /orders and PATCH /orders/{id}/status share the helper; MCP tools rely on them.
    created = client.post("/orders", headers=api_key_headers, json={
        "customer_name": "Astillero Norte",
        "items": [{"sku": "HW-WIN-10", "quantity": 1}],
    }).json()
    assert "inventory_deducted" in created and "items" in created

    patched = client.patch(f"/orders/{created['id']}/status", headers=api_key_headers,
                           json={"status": "pending"}).json()
    assert "inventory_deducted" in patched and "items" in patched


def test_customers_endpoint_was_removed(client, api_key_headers):
    assert client.get("/customers", headers=api_key_headers).status_code == 404
