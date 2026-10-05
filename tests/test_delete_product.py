"""DELETE /products/{product_id} — the response now includes the deleted product's sku."""


def _create(client, headers, sku="TEST-DEL-01"):
    return client.post("/products", headers=headers,
                       json={"name": "Producto de prueba", "sku": sku}).json()


def test_requires_auth(client, api_key_headers):
    product = _create(client, api_key_headers)
    assert client.delete(f"/products/{product['id']}").status_code == 401


def test_response_includes_sku(client, api_key_headers):
    product = _create(client, api_key_headers)
    res = client.delete(f"/products/{product['id']}", headers=api_key_headers)
    assert res.status_code == 200
    assert res.json() == {"deleted": True, "id": product["id"], "sku": "TEST-DEL-01"}


def test_product_is_actually_gone(client, api_key_headers):
    product = _create(client, api_key_headers)
    client.delete(f"/products/{product['id']}", headers=api_key_headers)
    assert client.get(f"/products/{product['id']}", headers=api_key_headers).status_code == 404


def test_unknown_product_is_404(client, api_key_headers):
    assert client.delete("/products/999", headers=api_key_headers).status_code == 404


def test_deleting_twice_is_404(client, api_key_headers):
    product = _create(client, api_key_headers)
    client.delete(f"/products/{product['id']}", headers=api_key_headers)
    assert client.delete(f"/products/{product['id']}", headers=api_key_headers).status_code == 404
