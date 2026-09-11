"""MCP tool search_orders, routed to the in-process API instead of over HTTP."""
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


def test_no_filters_sends_only_limit(api):
    body = mcp_server.search_orders()
    assert api == [("/orders/search", {"limit": 20})]
    assert body["count"] == 2


def test_filters_are_forwarded(api):
    body = mcp_server.search_orders(customer="marina", min_total=1000, status="accepted")
    assert api == [("/orders/search", {"customer": "marina", "min_total": 1000,
                                       "status": "accepted", "limit": 20})]
    assert [o["customer_name"] for o in body["items"]] == ["Blue Marina SL"]


def test_date_range_uses_api_param_names(api):
    body = mcp_server.search_orders(date_from="2001-01-01", date_to="2001-12-31")
    assert api[0][1] == {"from": "2001-01-01", "to": "2001-12-31", "limit": 20}
    assert body["items"] == []
