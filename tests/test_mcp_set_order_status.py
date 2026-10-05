"""MCP tool set_order_status — the result now includes previous_status."""
import pytest

import mcp_server

ORDER_ID = 1  # seed order, accepted


@pytest.fixture
def api(client, monkeypatch):
    """Route the MCP server's GETs and PATCHes to the test client."""
    calls = []

    def _get(path, params=None):
        calls.append(("GET", path, params))
        res = client.get(path, params=params, headers=mcp_server._headers())
        res.raise_for_status()
        return res.json()

    def _patch(path, json):
        calls.append(("PATCH", path, json))
        res = client.patch(path, json=json, headers=mcp_server._headers())
        res.raise_for_status()
        return res.json()

    monkeypatch.setattr(mcp_server, "_get", _get)
    monkeypatch.setattr(mcp_server, "_patch", _patch)
    return calls


def test_reports_previous_status(api):
    body = mcp_server.set_order_status(ORDER_ID, "cancelled")
    assert body["previous_status"] == "accepted"
    assert body["status"] == "cancelled"


def test_reads_before_writing(api):
    mcp_server.set_order_status(ORDER_ID, "pending")
    assert api == [
        ("GET", f"/orders/{ORDER_ID}", {"include_items": False}),
        ("PATCH", f"/orders/{ORDER_ID}/status", {"status": "pending"}),
    ]


def test_previous_status_follows_consecutive_changes(api):
    mcp_server.set_order_status(ORDER_ID, "pending")
    body = mcp_server.set_order_status(ORDER_ID, "accepted")
    assert body["previous_status"] == "pending"
    assert body["status"] == "accepted"


def test_rest_of_the_response_is_unchanged(api):
    body = mcp_server.set_order_status(ORDER_ID, "pending")
    assert {"id", "order_number", "status", "total", "items", "inventory_deducted"} <= body.keys()


def test_unknown_order_raises_without_patching(api):
    # The test client raises httpx2's HTTPStatusError; the real server raises httpx's.
    with pytest.raises(Exception) as err:
        mcp_server.set_order_status(999, "cancelled")
    assert err.value.response.status_code == 404
    assert [c[0] for c in api] == ["GET"]
