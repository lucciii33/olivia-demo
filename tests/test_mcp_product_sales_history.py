"""MCP tool product_sales_history, routed to the in-process API instead of over HTTP."""
import pytest

import mcp_server

# Seed: product 1 is the mainsail, sold 2 units (1440.0) in ORD-...-0001.
MAINSAIL_ID = 1


@pytest.fixture
def api(client, monkeypatch):
    """Send the MCP server's GETs to the test client, with the server's own headers."""
    calls = []

    def _get(path, params=None):
        calls.append((path, params))
        res = client.get(path, params=params, headers=mcp_server._headers())
        res.raise_for_status()
        return res.json()

    monkeypatch.setattr(mcp_server, "_get", _get)
    return calls


def test_history_for_seeded_product(api):
    body = mcp_server.product_sales_history(MAINSAIL_ID)
    assert api == [(f"/products/{MAINSAIL_ID}/orders", {"include_cancelled": False})]
    assert body["orders_count"] == 1
    assert body["units_sold"] == 2
    assert body["revenue"] == 1440.0


def test_include_cancelled_is_forwarded(api, client, api_key_headers):
    client.patch("/orders/1/status", headers=api_key_headers, json={"status": "cancelled"})
    assert mcp_server.product_sales_history(MAINSAIL_ID)["orders_count"] == 0
    body = mcp_server.product_sales_history(MAINSAIL_ID, include_cancelled=True)
    assert api[-1][1] == {"include_cancelled": True}
    assert body["orders_count"] == 1


def test_unknown_product_raises(api):
    # The test client raises its own HTTPStatusError class, so match on the message.
    with pytest.raises(Exception, match="404"):
        mcp_server.product_sales_history(9999)
