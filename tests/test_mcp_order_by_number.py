"""MCP tool order_by_number (new), plus the removal of sales_by_month."""
import asyncio

import pytest

import mcp_server


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


def _tool_names():
    return {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}


def test_calls_the_by_number_endpoint(api, client, api_key_headers):
    number = client.get("/orders/1", headers=api_key_headers).json()["order_number"]
    body = mcp_server.order_by_number(number)
    assert api == [(f"/orders/by-number/{number}", None)]
    assert body["id"] == 1
    assert body["customer_name"] == "Blue Marina SL"
    assert body["items_count"] == 2


def test_unknown_number_raises(api):
    # The test client raises httpx2's HTTPStatusError; the real server raises httpx's.
    with pytest.raises(Exception) as err:
        mcp_server.order_by_number("ORD-1999-9999")
    assert err.value.response.status_code == 404


def test_order_number_is_encoded(api):
    with pytest.raises(Exception):
        mcp_server.order_by_number("ORD 2026#1")
    assert api[0][0] == "/orders/by-number/ORD%202026%231"


def test_order_by_number_is_registered():
    assert "order_by_number" in _tool_names()


def test_sales_by_month_was_removed():
    assert not hasattr(mcp_server, "sales_by_month")
    assert "sales_by_month" not in _tool_names()


def test_sales_by_month_endpoint_still_exists(client, api_key_headers):
    # Only the MCP tool is gone; the API route stays.
    res = client.get("/stats/sales-by-month", headers=api_key_headers)
    assert res.status_code == 200
