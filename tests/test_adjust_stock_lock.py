"""POST /products/{id}/adjust-stock — expected_quantity lock and ?dry_run."""

TAPE_ID = 7  # ACC-TAPE-01, 3 in stock, minimum 10


def _adjust(client, headers, body, query=""):
    return client.post(f"/products/{TAPE_ID}/adjust-stock{query}", headers=headers, json=body)


def _stock(client, headers):
    return client.get(f"/products/{TAPE_ID}", headers=headers).json()["quantity"]


def test_matching_expected_quantity_applies(client, api_key_headers):
    res = _adjust(client, api_key_headers, {"delta": 2, "expected_quantity": 3})
    assert res.status_code == 200
    assert res.json()["product"]["quantity"] == 5
    assert res.json()["dry_run"] is False
    assert _stock(client, api_key_headers) == 5


def test_stale_expected_quantity_is_409(client, api_key_headers):
    res = _adjust(client, api_key_headers, {"delta": 2, "expected_quantity": 4})
    assert res.status_code == 409
    assert res.json()["detail"] == "Stock changed: expected 4, current 3"
    assert _stock(client, api_key_headers) == 3


def test_expected_quantity_is_optional(client, api_key_headers):
    assert _adjust(client, api_key_headers, {"delta": 1}).status_code == 200


def test_negative_expected_quantity_is_422(client, api_key_headers):
    assert _adjust(client, api_key_headers, {"delta": 1, "expected_quantity": -1}).status_code == 422


def test_lock_is_checked_before_stock(client, api_key_headers):
    # Both wrong: the stale lock wins over "not enough stock".
    res = _adjust(client, api_key_headers, {"delta": -10, "expected_quantity": 99})
    assert res.json()["detail"] == "Stock changed: expected 99, current 3"


def test_zero_delta_is_checked_before_lock(client, api_key_headers):
    res = _adjust(client, api_key_headers, {"delta": 0, "expected_quantity": 99})
    assert res.status_code == 422
    assert res.json()["detail"] == "delta cannot be 0"


def test_dry_run_previews_without_saving(client, api_key_headers):
    res = _adjust(client, api_key_headers, {"delta": 8}, "?dry_run=true")
    assert res.status_code == 200
    body = res.json()
    assert body["dry_run"] is True
    assert body["previous_quantity"] == 3
    assert body["product"]["quantity"] == 11
    assert body["product"]["low_stock"] is False
    assert _stock(client, api_key_headers) == 3


def test_dry_run_still_validates(client, api_key_headers):
    res = _adjust(client, api_key_headers, {"delta": -4}, "?dry_run=true")
    assert res.status_code == 409
    assert res.json()["detail"] == "Not enough stock: have 3, delta -4"
    res = _adjust(client, api_key_headers, {"delta": 1, "expected_quantity": 0}, "?dry_run=true")
    assert res.status_code == 409


def test_dry_run_false_saves(client, api_key_headers):
    _adjust(client, api_key_headers, {"delta": 1}, "?dry_run=false")
    assert _stock(client, api_key_headers) == 4


def test_invalid_dry_run_value_is_422(client, api_key_headers):
    assert _adjust(client, api_key_headers, {"delta": 1}, "?dry_run=maybe").status_code == 422
