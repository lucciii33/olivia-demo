"""MCP tool business_dashboard — top_limit controls how many top sellers come back."""
import asyncio

import pytest

import mcp_server

# Seed orders sold four distinct products; the shackles lead with 10 units.
SEED_TOP_SELLERS = 4


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


def test_default_keeps_top_five(api):
    body = mcp_server.business_dashboard()
    assert api == [("/stats/overview", None), ("/stats/top-products", {"limit": 5})]
    assert len(body["top_products"]) == SEED_TOP_SELLERS


def test_top_limit_is_forwarded(api):
    body = mcp_server.business_dashboard(top_limit=2)
    assert api[1] == ("/stats/top-products", {"limit": 2})
    assert [p["sku"] for p in body["top_products"]] == ["HW-SHK-08", "ACC-TELL-01"]


def test_response_shape_is_unchanged(api):
    body = mcp_server.business_dashboard(top_limit=1)
    assert set(body) == {"overview", "top_products"}
    assert body["overview"]["orders"] == 2


def test_top_limit_is_in_the_tool_schema():
    tool = next(t for t in asyncio.run(mcp_server.mcp.list_tools())
                if t.name == "business_dashboard")
    schema = tool.input_schema
    assert schema["properties"]["top_limit"]["default"] == 5
    assert schema.get("required", []) == []
