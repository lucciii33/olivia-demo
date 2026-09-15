"""MCP tool create_order — the customer_phone param reaches the API."""
import pytest

import mcp_server

ITEMS = [{"sku": "HW-WIN-10", "quantity": 1}]


@pytest.fixture
def api(client, monkeypatch):
    """Send the MCP server's POSTs to the test client, with the server's own headers."""
    calls = []

    def _post(path, json):
        calls.append((path, json))
        res = client.post(path, json=json, headers=mcp_server._headers())
        res.raise_for_status()
        return res.json()

    monkeypatch.setattr(mcp_server, "_post", _post)
    return calls


def test_customer_phone_is_saved(api):
    order = mcp_server.create_order("Astillero Norte", ITEMS, customer_phone="+34 600 000 000")
    assert api[0][1]["customer_phone"] == "+34 600 000 000"
    assert order["customer_phone"] == "+34 600 000 000"


def test_customer_phone_is_optional(api):
    order = mcp_server.create_order("Astillero Norte", ITEMS)
    assert api[0][1]["customer_phone"] is None
    assert order["customer_phone"] is None


def test_existing_params_still_work(api):
    order = mcp_server.create_order("Astillero Norte", ITEMS,
                                    customer_email="compras@astillero.example",
                                    notes="entrega urgente")
    assert api == [("/orders", {
        "customer_name": "Astillero Norte",
        "customer_email": "compras@astillero.example",
        "customer_phone": None,
        "items": ITEMS,
        "notes": "entrega urgente",
    })]
    assert order["customer_email"] == "compras@astillero.example"
    assert order["notes"] == "entrega urgente"


def test_positional_arguments_keep_their_meaning(api):
    # customer_phone was added last, so existing positional calls are unaffected.
    mcp_server.create_order("Astillero Norte", ITEMS, "a@b.example", "nota")
    assert api[0][1]["customer_email"] == "a@b.example"
    assert api[0][1]["notes"] == "nota"
