"""GET /orders/{id}/invoice?currency= — the total also shown in EUR or GBP."""

ORDER_ID = 1  # seed invoice total at 21% tax: 1833.15 USD


def _invoice(client, headers, query=""):
    return client.get(f"/orders/{ORDER_ID}/invoice{query}", headers=headers)


def test_default_is_usd(client, api_key_headers):
    body = _invoice(client, api_key_headers).json()
    assert body["converted_currency"] == "USD"
    assert body["exchange_rate"] == 1.0
    assert body["converted_total"] == body["total"] == 1833.15


def test_eur(client, api_key_headers):
    body = _invoice(client, api_key_headers, "?currency=EUR").json()
    assert body["exchange_rate"] == 0.92
    assert body["converted_total"] == 1686.5
    assert body["total"] == 1833.15  # still USD
    assert body["currency"] == "USD"


def test_gbp(client, api_key_headers):
    body = _invoice(client, api_key_headers, "?currency=GBP").json()
    assert body["exchange_rate"] == 0.79
    assert body["converted_total"] == 1448.19


def test_converts_the_total_after_discount_and_tax(client, api_key_headers):
    body = _invoice(client, api_key_headers, "?currency=EUR&discount_percent=10&tax_rate=10").json()
    assert body["total"] == 1499.85
    assert body["converted_total"] == 1379.86


def test_unsupported_or_lowercase_currency_is_422(client, api_key_headers):
    for currency in ("JPY", "eur", "", "EURO"):
        assert _invoice(client, api_key_headers, f"?currency={currency}").status_code == 422, currency
