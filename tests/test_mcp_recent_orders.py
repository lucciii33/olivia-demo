"""MCP tool recent_orders — the five newest orders, no arguments."""
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


def _order(client, headers, customer):
    return client.post("/orders", headers=headers, json={
        "customer_name": customer,
        "items": [{"sku": "HW-SHK-08", "quantity": 1}],
    }).json()


def test_calls_orders_with_limit_five(api):
    mcp_server.recent_orders()
    assert api == [("/orders", {"limit": 5})]


def test_seed_orders_newest_first(api):
    body = mcp_server.recent_orders()
    assert body["count"] == 2
    assert [o["order_number"][-4:] for o in body["items"]] == ["0002", "0001"]


def test_returns_only_the_five_newest(api, client, api_key_headers):
    created = [_order(client, api_key_headers, f"Cliente {n}") for n in range(6)]
    body = mcp_server.recent_orders()
    assert body["count"] == 5
    assert body["total_count"] == 8
    assert [o["id"] for o in body["items"]] == [o["id"] for o in reversed(created)][:5]


def test_takes_no_arguments():
    tool = next(t for t in asyncio.run(mcp_server.mcp.list_tools()) if t.name == "recent_orders")
    assert tool.input_schema.get("properties", {}) == {}
