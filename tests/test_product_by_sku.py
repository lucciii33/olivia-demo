"""GET /products/by-sku/{sku} — look a product up by its SKU instead of its id."""

MAINSAIL_ID, MAINSAIL_SKU = 1, "SAIL-MAIN-052"


def test_requires_auth(client):
    assert client.get(f"/products/by-sku/{MAINSAIL_SKU}").status_code == 401


def test_same_body_as_lookup_by_id(client, api_key_headers):
    by_sku = client.get(f"/products/by-sku/{MAINSAIL_SKU}", headers=api_key_headers)
    by_id = client.get(f"/products/{MAINSAIL_ID}", headers=api_key_headers)
    assert by_sku.status_code == 200
    assert by_sku.json() == by_id.json()
    assert by_sku.json()["name"] == "Mainsail Dacron 5.2m"


def test_includes_low_stock_flag(client, api_key_headers):
    body = client.get("/products/by-sku/ACC-TAPE-01", headers=api_key_headers).json()
    assert body["low_stock"] is True


def test_unknown_sku_is_404(client, api_key_headers):
    res = client.get("/products/by-sku/NO-EXISTE", headers=api_key_headers)
    assert res.status_code == 404
    assert "NO-EXISTE" in res.json()["detail"]


def test_match_is_exact(client, api_key_headers):
    for partial in ("SAIL-MAIN", "sail-main-052"):
        assert client.get(f"/products/by-sku/{partial}", headers=api_key_headers).status_code == 404


def test_new_products_are_found(client, api_key_headers):
    created = client.post("/products", headers=api_key_headers,
                          json={"name": "Producto nuevo", "sku": "NEW-001"}).json()
    body = client.get("/products/by-sku/NEW-001", headers=api_key_headers).json()
    assert body["id"] == created["id"]


def test_does_not_clash_with_product_orders_route(client, api_key_headers):
    # A SKU literally called "orders" must hit this endpoint, and
    # /products/{id}/orders must keep working.
    created = client.post("/products", headers=api_key_headers,
                          json={"name": "Nombre raro", "sku": "orders"}).json()
    assert client.get("/products/by-sku/orders", headers=api_key_headers).json()["id"] == created["id"]
    history = client.get(f"/products/{MAINSAIL_ID}/orders", headers=api_key_headers)
    assert history.status_code == 200
    assert history.json()["orders_count"] == 1
