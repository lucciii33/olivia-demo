"""MCP tool get_product_by_sku, routed to the in-process API instead of over HTTP."""
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


def test_calls_the_by_sku_endpoint(api):
    body = mcp_server.get_product_by_sku("SAIL-MAIN-052")
    assert api == [("/products/by-sku/SAIL-MAIN-052", None)]
    assert body["id"] == 1
    assert body["name"] == "Mainsail Dacron 5.2m"


def test_unknown_sku_raises(api):
    # The test client raises httpx2's HTTPStatusError; the real server raises httpx's.
    # Both carry the response, which is what matters here.
    with pytest.raises(Exception) as err:
        mcp_server.get_product_by_sku("NO-EXISTE")
    assert err.value.response.status_code == 404


def test_special_characters_are_encoded(api, client, api_key_headers):
    # Unencoded, '#' would start a URL fragment and the lookup would miss.
    created = client.post("/products", headers=api_key_headers,
                          json={"name": "Kit", "sku": "KIT#1"}).json()
    body = mcp_server.get_product_by_sku("KIT#1")
    assert api[-1][0] == "/products/by-sku/KIT%231"
    assert body["id"] == created["id"]


def test_tool_is_registered():
    names = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert "get_product_by_sku" in names
