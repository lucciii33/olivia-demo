"""MCP tool sales_by_month, routed to the in-process API instead of over HTTP."""
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


def test_all_years(api):
    body = mcp_server.sales_by_month()
    assert api == [("/stats/sales-by-month", None)]
    assert body["year"] is None
    assert body["totals"] == {"orders": 2, "units_sold": 17, "revenue": 2349.0}


def test_year_is_forwarded(api):
    body = mcp_server.sales_by_month(year=2001)
    assert api == [("/stats/sales-by-month", {"year": 2001})]
    assert body["year"] == 2001
    assert body["months"] == []
