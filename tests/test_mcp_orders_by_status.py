"""MCP tool orders_by_status (new) and the removal of adjust_stock."""
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


def test_calls_the_orders_by_status_endpoint(api):
    body = mcp_server.orders_by_status()
    assert api == [("/stats/orders-by-status", None)]
    by_status = {s["status"]: s for s in body["statuses"]}
    assert body["total_orders"] == 2
    assert by_status["accepted"] == {"status": "accepted", "orders": 2, "total": 2349.0}
    assert by_status["cancelled"]["orders"] == 0


def test_orders_by_status_is_registered():
    assert "orders_by_status" in _tool_names()


def test_adjust_stock_was_removed():
    assert not hasattr(mcp_server, "adjust_stock")
    assert "adjust_stock" not in _tool_names()


def test_adjust_stock_endpoint_still_exists(client, api_key_headers):
    # Only the MCP tool is gone; the API route stays.
    res = client.post("/products/7/adjust-stock", headers=api_key_headers, json={"delta": 1})
    assert res.status_code == 200


def test_cancelled_percent_is_zero_with_seed(api):
    assert mcp_server.orders_by_status()["cancelled_percent"] == 0.0


def test_cancelled_percent_after_cancelling(api, client, api_key_headers):
    order = client.post("/orders", headers=api_key_headers, json={
        "customer_name": "Astillero Norte",
        "items": [{"sku": "HW-WIN-10", "quantity": 1}],
    }).json()
    client.patch(f"/orders/{order['id']}/status", headers=api_key_headers,
                 json={"status": "cancelled"})
    assert mcp_server.orders_by_status()["cancelled_percent"] == 33.3  # 1 of 3

