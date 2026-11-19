"""GET /products/{id}/quote — price quote with volume discount tiers."""

TAPE_ID = 7  # ACC-TAPE-01, sells at 14.0, 3 in stock


def _quote(client, headers, quantity=None, product_id=TAPE_ID):
    params = {} if quantity is None else {"quantity": quantity}
    return client.get(f"/products/{product_id}/quote", headers=headers, params=params)


def test_requires_auth(client):
    assert client.get(f"/products/{TAPE_ID}/quote?quantity=1").status_code == 401


def test_no_discount_below_ten(client, api_key_headers):
    assert _quote(client, api_key_headers, 9).json() == {
        "product_id": TAPE_ID, "sku": "ACC-TAPE-01", "quantity": 9, "unit_price": 14.0,
        "subtotal": 126.0, "volume_discount_percent": 0, "discount": 0.0, "coupon": None,
        "coupon_discount_percent": 0, "coupon_discount": 0.0, "total": 126.0, "currency": "USD",
    }


def test_five_percent_from_ten(client, api_key_headers):
    body = _quote(client, api_key_headers, 10).json()
    assert body["volume_discount_percent"] == 5
    assert body["discount"] == 7.0
    assert body["total"] == 133.0
    assert _quote(client, api_key_headers, 49).json()["volume_discount_percent"] == 5


def test_ten_percent_from_fifty(client, api_key_headers):
    body = _quote(client, api_key_headers, 50).json()
    assert body["volume_discount_percent"] == 10
    assert body["subtotal"] == 700.0
    assert body["discount"] == 70.0
    assert body["total"] == 630.0


def test_stock_is_not_checked_or_changed(client, api_key_headers):
    assert _quote(client, api_key_headers, 1000).status_code == 200  # only 3 in stock
    assert client.get(f"/products/{TAPE_ID}", headers=api_key_headers).json()["quantity"] == 3


def test_quantity_is_required_and_bounded(client, api_key_headers):
    for quantity in (None, 0, -1, 1001, "abc"):
        assert _quote(client, api_key_headers, quantity).status_code == 422, quantity
    assert _quote(client, api_key_headers, 1).status_code == 200


def test_unknown_product(client, api_key_headers):
    res = _quote(client, api_key_headers, 1, product_id=9999)
    assert res.status_code == 404
    assert res.json()["detail"] == "Product not found"


# --- 100+ tier and coupons ---

def _q(client, headers, **params):
    return client.get(f"/products/{TAPE_ID}/quote", headers=headers, params=params)


def test_fifteen_percent_tier(client, api_key_headers):
    body = _q(client, api_key_headers, quantity=101).json()
    assert body["volume_discount_percent"] == 15
    assert body["total"] == 1201.9


def test_ninety_nine_is_still_ten_percent(client, api_key_headers):
    assert _q(client, api_key_headers, quantity=99).json()["volume_discount_percent"] == 10


def test_coupon_applies_after_volume_discount(client, api_key_headers):
    body = _q(client, api_key_headers, quantity=10, coupon="SAIL5").json()
    assert body["discount"] == 7.0
    assert body["coupon"] == "SAIL5"
    assert body["coupon_discount_percent"] == 5
    assert body["coupon_discount"] == 6.65
    assert body["total"] == 126.35


def test_sail10(client, api_key_headers):
    body = _q(client, api_key_headers, quantity=1, coupon="SAIL10").json()
    assert body["coupon_discount"] == 1.4
    assert body["total"] == 12.6


def test_no_coupon(client, api_key_headers):
    body = _q(client, api_key_headers, quantity=1).json()
    assert body["coupon"] is None
    assert body["coupon_discount"] == 0
    assert body["total"] == 14.0


def test_unknown_coupon_is_400(client, api_key_headers):
    res = _q(client, api_key_headers, quantity=1, coupon="FREE")
    assert res.status_code == 400
    assert res.json()["detail"] == "Unknown coupon 'FREE'"
