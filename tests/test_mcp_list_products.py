"""MCP tool list_products (offset, has_more, no description) and check_low_stock removal."""
import asyncio

import pytest

import mcp_server

SEED_PRODUCTS = 8
SEED_LOW_STOCK = 2


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


def test_defaults_ask_for_one_extra_row(api):
    body = mcp_server.list_products()
    assert api == [("/products", {"q": None, "low_stock": False, "limit": 21, "offset": 0})]
    assert body["count"] == SEED_PRODUCTS
    assert body["has_more"] is False


def test_description_is_left_out(api):
    items = mcp_server.list_products()["items"]
    assert items and all("description" not in p for p in items)
    assert all({"id", "sku", "name", "quantity"} <= p.keys() for p in items)


def test_has_more_when_another_page_exists(api):
    body = mcp_server.list_products(limit=3)
    assert body["count"] == 3
    assert len(body["items"]) == 3
    assert body["has_more"] is True


def test_exact_fit_has_no_more(api):
    body = mcp_server.list_products(limit=SEED_PRODUCTS)
    assert body["count"] == SEED_PRODUCTS
    assert body["has_more"] is False


def test_offset_pages_cover_everything_once(api):
    seen, offset = [], 0
    while True:
        page = mcp_server.list_products(limit=3, offset=offset)
        seen += [p["id"] for p in page["items"]]
        if not page["has_more"]:
            break
        offset += 3
    assert offset == 6
    assert len(seen) == SEED_PRODUCTS == len(set(seen))


def test_low_stock_filter_still_works(api):
    body = mcp_server.list_products(low_stock_only=True)
    assert body["count"] == SEED_LOW_STOCK
    assert api[0][1]["low_stock"] is True


def test_check_low_stock_was_removed():
    assert not hasattr(mcp_server, "check_low_stock")
    names = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert "check_low_stock" not in names
