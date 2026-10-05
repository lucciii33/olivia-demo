"""MCP tool reorder_suggestions — what to restock, no arguments."""
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


def test_calls_the_reorder_suggestions_endpoint(api):
    body = mcp_server.reorder_suggestions()
    assert api == [("/products/reorder-suggestions", None)]
    assert body["count"] == 2
    assert body["total_units"] == 157
    assert body["estimated_cost"] == 396.0
    assert [i["sku"] for i in body["items"]] == ["ACC-TAPE-01", "LINE-DYN-06"]


def test_takes_no_arguments():
    tool = next(t for t in asyncio.run(mcp_server.mcp.list_tools())
                if t.name == "reorder_suggestions")
    assert tool.input_schema.get("properties", {}) == {}
