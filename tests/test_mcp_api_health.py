"""MCP tool api_health — checks the API is up, with no arguments."""
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


def test_calls_health(api):
    body = mcp_server.api_health()
    assert api == [("/health", None)]
    assert body["status"] == "ok"


def test_takes_no_arguments():
    tool = next(t for t in asyncio.run(mcp_server.mcp.list_tools()) if t.name == "api_health")
    assert tool.input_schema.get("properties", {}) == {}
