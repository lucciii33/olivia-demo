"""GET /products — total_count, has_more, sort and parameter validation."""

SEED_PRODUCTS = 8


def _list(client, headers, query=""):
    return client.get(f"/products{query}", headers=headers)


def _skus(res):
    return [p["sku"] for p in res.json()["items"]]


def test_total_count_and_has_more(client, api_key_headers):
    body = _list(client, api_key_headers, "?limit=3").json()
    assert body["count"] == 3
    assert body["total_count"] == SEED_PRODUCTS
    assert body["has_more"] is True
    last = _list(client, api_key_headers, "?limit=3&offset=6").json()
    assert last["count"] == 2
    assert last["has_more"] is False


def test_total_count_respects_filters(client, api_key_headers):
    body = _list(client, api_key_headers, "?low_stock=true&limit=1").json()
    assert body["total_count"] == 2
    assert body["has_more"] is True
    assert _list(client, api_key_headers, "?q=SAIL-").json()["total_count"] == 3


def test_default_sort_is_name(client, api_key_headers):
    body = _list(client, api_key_headers).json()
    assert body["sort"] == "name"
    names = [p["name"] for p in body["items"]]
    assert names == sorted(names)


def test_sort_by_price_and_stock(client, api_key_headers):
    assert _skus(_list(client, api_key_headers, "?sort=price_desc&limit=3")) == \
        ["SAIL-SPIN-15", "SAIL-GEN-135", "SAIL-MAIN-052"]
    assert _skus(_list(client, api_key_headers, "?sort=price_asc&limit=2")) == \
        ["LINE-DYN-06", "ACC-TELL-01"]
    assert _skus(_list(client, api_key_headers, "?sort=stock_asc&limit=2")) == \
        ["ACC-TAPE-01", "SAIL-SPIN-15"]


def test_pages_do_not_overlap(client, api_key_headers):
    seen = []
    for offset in range(0, SEED_PRODUCTS, 3):
        seen += _skus(_list(client, api_key_headers, f"?sort=price_asc&limit=3&offset={offset}"))
    assert len(seen) == len(set(seen)) == SEED_PRODUCTS


def test_invalid_parameters(client, api_key_headers):
    for query in ("?sort=sku", "?limit=0", "?offset=-1"):
        assert _list(client, api_key_headers, query).status_code == 422, query
