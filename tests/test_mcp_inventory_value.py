"""MCP tool inventory_value — stock valued at cost and at sale price, no arguments."""
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


def test_calls_the_inventory_value_endpoint(api, client, api_key_headers):
    body = mcp_server.inventory_value()
    assert api == [("/stats/inventory-value", None)]
    overview = client.get("/stats/overview", headers=api_key_headers).json()
    assert body["cost_value"] == overview["inventory_cost_value"]
    assert body["potential_margin"] == round(body["retail_value"] - body["cost_value"], 2)


def test_takes_no_arguments():
    tool = next(t for t in asyncio.run(mcp_server.mcp.list_tools()) if t.name == "inventory_value")
    assert tool.input_schema.get("properties", {}) == {}
