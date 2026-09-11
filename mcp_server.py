"""
Sailtrim Demo MCP server — 10 tools.

The MCP tools call the protected REST API over HTTP, authenticating with the
API key (or Bearer token). This proves the auth layer end to end and keeps a
single source of truth (the API).

Run the API first (python app.py), then run this server:
    python mcp_server.py                          # stdio (local clients)
    MCP_TRANSPORT=streamable-http python mcp_server.py   # HTTP on :9000
"""
import os

import httpx

# mcp 1.x exposes FastMCP; mcp 2.x renamed it to MCPServer. Support both.
try:
    from mcp.server.fastmcp import FastMCP as _MCP
except ModuleNotFoundError:
    from mcp.server.mcpserver import MCPServer as _MCP

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "demo-api-key-123")
BEARER_TOKEN = os.getenv("BEARER_TOKEN", "")

# Transport: "stdio" (default, for Claude Desktop and other local clients) or
# "streamable-http" / "sse" when the client connects over the network.
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
# $PORT is what Render assigns; MCP_PORT overrides it for local runs.
MCP_PORT = int(os.getenv("MCP_PORT") or os.getenv("PORT", "9000"))

mcp = _MCP("sailtrim-demo")


def _headers():
    # Send whichever credential is configured. The API accepts either one.
    if BEARER_TOKEN:
        return {"Authorization": f"Bearer {BEARER_TOKEN}"}
    return {"X-API-Key": API_KEY}


def _get(path, params=None):
    with httpx.Client(timeout=15) as c:
        r = c.get(f"{API_BASE}{path}", params=params, headers=_headers())
        r.raise_for_status()
        return r.json()


def _post(path, json):
    with httpx.Client(timeout=15) as c:
        r = c.post(f"{API_BASE}{path}", json=json, headers=_headers())
        r.raise_for_status()
        return r.json()


def _patch(path, json):
    with httpx.Client(timeout=15) as c:
        r = c.patch(f"{API_BASE}{path}", json=json, headers=_headers())
        r.raise_for_status()
        return r.json()


# 1
@mcp.tool()
def list_products(query: str = "", low_stock_only: bool = False, limit: int = 20) -> dict:
    """List inventory products, optionally filtered by a search term or low-stock flag."""
    return _get("/products", {"q": query or None, "low_stock": low_stock_only, "limit": limit})


# 2
@mcp.tool()
def get_product(product_id: int) -> dict:
    """Get full details of a single product by its numeric id."""
    return _get(f"/products/{product_id}")


# 3
@mcp.tool()
def check_low_stock() -> dict:
    """Return every product at or below its minimum stock threshold (reorder alerts)."""
    return _get("/products/low-stock")


# 4
@mcp.tool()
def adjust_stock(product_id: int, delta: int, reason: str = "") -> dict:
    """Adjust a product's stock. Use a positive delta to add units, negative to remove."""
    return _post(f"/products/{product_id}/adjust-stock", {"delta": delta, "reason": reason})


# 5
@mcp.tool()
def create_order(customer_name: str, items: list[dict], customer_email: str = "",
                 notes: str = "") -> dict:
    """Create an order and deduct stock.
    `items` is a list like [{"sku": "SAIL-MAIN-052", "quantity": 2}]."""
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email or None,
        "items": items,
        "notes": notes or None,
    }
    return _post("/orders", payload)


# 6
@mcp.tool()
def set_order_status(order_id: int, status: str) -> dict:
    """Update an order's status (pending | accepted | cancelled). Cancelling restocks items."""
    return _patch(f"/orders/{order_id}/status", {"status": status})


# 7
@mcp.tool()
def business_dashboard() -> dict:
    """Get a business snapshot: inventory value, revenue, low-stock count and top sellers."""
    overview = _get("/stats/overview")
    top = _get("/stats/top-products", {"limit": 5})
    return {"overview": overview, "top_products": top["items"]}


# 8
@mcp.tool()
def sales_by_month(year: int | None = None) -> dict:
    """Monthly sales (orders, units sold, revenue) excluding cancelled orders.
    Pass `year` to limit the report to one calendar year."""
    return _get("/stats/sales-by-month", {"year": year} if year is not None else None)


# 9
@mcp.tool()
def search_orders(date_from: str = "", date_to: str = "", customer: str = "",
                  min_total: float | None = None, status: str = "", limit: int = 20) -> dict:
    """Search orders by date range (YYYY-MM-DD, inclusive), customer name/email,
    minimum total and status (pending | accepted | cancelled). All filters combine."""
    params = {
        "from": date_from or None,
        "to": date_to or None,
        "customer": customer or None,
        "min_total": min_total,
        "status": status or None,
        "limit": limit,
    }
    return _get("/orders/search", {k: v for k, v in params.items() if v is not None})


# 10
@mcp.tool()
def product_sales_history(product_id: int, include_cancelled: bool = False) -> dict:
    """Every order that included a product, with units sold and revenue.
    Cancelled orders are left out unless include_cancelled is true."""
    return _get(f"/products/{product_id}/orders", {"include_cancelled": include_cancelled})


if __name__ == "__main__":
    if MCP_TRANSPORT == "stdio":
        mcp.run()
    else:
        # Network transports need a host and port; stdio takes neither.
        mcp.run(transport=MCP_TRANSPORT, host=MCP_HOST, port=MCP_PORT)
