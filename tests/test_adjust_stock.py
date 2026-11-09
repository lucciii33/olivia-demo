"""POST /products/{id}/adjust-stock — delta 0, 409 on not enough stock, previous_quantity."""

TAPE_ID = 7  # ACC-TAPE-01, 3 in stock


def _adjust(client, headers, delta, product_id=TAPE_ID):
    return client.post(f"/products/{product_id}/adjust-stock", headers=headers,
                       json={"delta": delta, "reason": "QA"})


def test_response_includes_previous_quantity(client, api_key_headers):
    body = _adjust(client, api_key_headers, 5).json()
    assert body["previous_quantity"] == 3
    assert body["product"]["quantity"] == 8
    assert body["applied_delta"] == 5
    assert body["reason"] == "QA"


def test_can_remove_down_to_zero(client, api_key_headers):
    body = _adjust(client, api_key_headers, -3).json()
    assert body["previous_quantity"] == 3
    assert body["product"]["quantity"] == 0


def test_not_enough_stock_is_409(client, api_key_headers):
    res = _adjust(client, api_key_headers, -4)
    assert res.status_code == 409
    assert res.json()["detail"] == "Not enough stock: have 3, delta -4"
    assert client.get(f"/products/{TAPE_ID}", headers=api_key_headers).json()["quantity"] == 3


def test_zero_delta_is_rejected(client, api_key_headers):
    res = _adjust(client, api_key_headers, 0)
    assert res.status_code == 422
    assert res.json()["detail"] == "delta cannot be 0"


def test_unknown_product(client, api_key_headers):
    assert _adjust(client, api_key_headers, 1, product_id=9999).status_code == 404
