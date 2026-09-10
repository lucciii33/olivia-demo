"""
Sailtrim Demo API — Inventory & Orders
FastAPI + SQLite. Exactly 19 endpoints.

Auth: every endpoint except GET /health requires EITHER an API key
(X-API-Key header) OR a Bearer token (Authorization: Bearer <token>).
"""
import os
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from auth import require_auth
from db import get_conn, init_db, now_iso

app = FastAPI(
    title="Sailtrim Demo API",
    description="Inventory & Orders demo — protected by API key or Bearer token.",
    version="1.0.0",
)


@app.on_event("startup")
def _startup():
    init_db(seed=True)


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class ProductIn(BaseModel):
    name: str
    sku: str
    description: Optional[str] = None
    quantity: int = 0
    minimum_stock: int = 0
    unit: str = "unit"
    cost_price: float = 0
    sale_price: float = 0
    currency: str = "USD"


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[int] = None
    minimum_stock: Optional[int] = None
    unit: Optional[str] = None
    cost_price: Optional[float] = None
    sale_price: Optional[float] = None
    currency: Optional[str] = None


class StockAdjust(BaseModel):
    delta: int = Field(..., description="Positive to add stock, negative to remove")
    reason: Optional[str] = None


class BulkAdjustItem(BaseModel):
    sku: str
    delta: int = Field(..., description="Positive to add stock, negative to remove")


class BulkAdjustIn(BaseModel):
    items: list[BulkAdjustItem] = Field(..., min_length=1, max_length=100)
    reason: Optional[str] = None


class OrderItemIn(BaseModel):
    sku: str
    quantity: int = Field(..., gt=0)


class OrderIn(BaseModel):
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    items: list[OrderItemIn]
    notes: Optional[str] = None


class StatusIn(BaseModel):
    status: str = Field(..., description="pending | accepted | cancelled")


def _product_dict(row):
    d = dict(row)
    d["low_stock"] = d["quantity"] <= d["minimum_stock"]
    return d


def _valid_date(value):
    """True if value is a plain YYYY-MM-DD date."""
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _generate_order_number(conn):
    c = conn.execute("SELECT COUNT(*) AS c FROM orders").fetchone()["c"]
    return f"ORD-{datetime.now().year}-{(c + 1):04d}"


# --------------------------------------------------------------------------- #
# 1. Health (public)
# --------------------------------------------------------------------------- #
@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "sailtrim-demo-api", "time": now_iso()}


# --------------------------------------------------------------------------- #
# Products
# --------------------------------------------------------------------------- #
# 2. Create product
@app.post("/products", tags=["products"], dependencies=[Depends(require_auth)])
def create_product(body: ProductIn):
    conn = get_conn()
    try:
        ts = now_iso()
        try:
            cur = conn.execute(
                """INSERT INTO products
                (name, sku, description, quantity, minimum_stock, unit,
                 cost_price, sale_price, currency, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (body.name, body.sku, body.description, body.quantity,
                 body.minimum_stock, body.unit, body.cost_price,
                 body.sale_price, body.currency, ts, ts),
            )
        except Exception:
            raise HTTPException(status_code=409, detail=f"SKU '{body.sku}' already exists")
        conn.commit()
        row = conn.execute("SELECT * FROM products WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _product_dict(row)
    finally:
        conn.close()


# 3. List products (with search + low-stock filter)
@app.get("/products", tags=["products"], dependencies=[Depends(require_auth)])
def list_products(
    q: Optional[str] = Query(None, description="Search name or SKU"),
    low_stock: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    conn = get_conn()
    try:
        sql = "SELECT * FROM products WHERE 1=1"
        args: list = []
        if q:
            sql += " AND (name LIKE ? OR sku LIKE ?)"
            args += [f"%{q}%", f"%{q}%"]
        if low_stock:
            sql += " AND quantity <= minimum_stock"
        sql += " ORDER BY name LIMIT ? OFFSET ?"
        args += [limit, offset]
        rows = conn.execute(sql, args).fetchall()
        return {"count": len(rows), "items": [_product_dict(r) for r in rows]}
    finally:
        conn.close()


# 4. Low-stock products (dedicated route)
@app.get("/products/low-stock", tags=["products"], dependencies=[Depends(require_auth)])
def low_stock_products():
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM products WHERE quantity <= minimum_stock ORDER BY quantity ASC"
        ).fetchall()
        return {"count": len(rows), "items": [_product_dict(r) for r in rows]}
    finally:
        conn.close()


# 19. Bulk stock adjustment (all or nothing)
# Declared before the /products/{product_id} routes, like /products/low-stock.
@app.post("/products/bulk-adjust", tags=["products"], dependencies=[Depends(require_auth)])
def bulk_adjust_stock(body: BulkAdjustIn):
    skus = [item.sku for item in body.items]
    duplicates = sorted({s for s in skus if skus.count(s) > 1})
    if duplicates:
        raise HTTPException(status_code=400,
                            detail=f"Each SKU may appear once; repeated: {', '.join(duplicates)}")
    conn = get_conn()
    try:
        # Validate every line before writing anything, so a bad line leaves
        # the whole inventory untouched.
        plan = []
        for item in body.items:
            row = conn.execute("SELECT * FROM products WHERE sku = ?", (item.sku,)).fetchone()
            if not row:
                raise HTTPException(status_code=400, detail=f"Unknown SKU '{item.sku}'")
            new_qty = row["quantity"] + item.delta
            if new_qty < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for {item.sku}: have {row['quantity']}, delta {item.delta}",
                )
            plan.append((row, item.delta, new_qty))

        ts = now_iso()
        for row, _, new_qty in plan:
            conn.execute("UPDATE products SET quantity = ?, updated_at = ? WHERE id = ?",
                         (new_qty, ts, row["id"]))
        conn.commit()

        adjusted = []
        for row, delta, _ in plan:
            updated = _product_dict(
                conn.execute("SELECT * FROM products WHERE id = ?", (row["id"],)).fetchone())
            adjusted.append({
                "product_id": updated["id"],
                "sku": updated["sku"],
                "previous_quantity": row["quantity"],
                "delta": delta,
                "quantity": updated["quantity"],
                "low_stock": updated["low_stock"],
            })
        return {"count": len(adjusted), "reason": body.reason, "adjusted": adjusted}
    finally:
        conn.close()


# 5. Get product
@app.get("/products/{product_id}", tags=["products"], dependencies=[Depends(require_auth)])
def get_product(product_id: int):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Product not found")
        return _product_dict(row)
    finally:
        conn.close()


# 6. Update product
@app.put("/products/{product_id}", tags=["products"], dependencies=[Depends(require_auth)])
def update_product(product_id: int, body: ProductUpdate):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Product not found")
        fields = {k: v for k, v in body.model_dump().items() if v is not None}
        if fields:
            fields["updated_at"] = now_iso()
            sets = ", ".join(f"{k} = ?" for k in fields)
            conn.execute(f"UPDATE products SET {sets} WHERE id = ?",
                         [*fields.values(), product_id])
            conn.commit()
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return _product_dict(row)
    finally:
        conn.close()


# 7. Delete product
@app.delete("/products/{product_id}", tags=["products"], dependencies=[Depends(require_auth)])
def delete_product(product_id: int):
    conn = get_conn()
    try:
        cur = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Product not found")
        return {"deleted": True, "id": product_id}
    finally:
        conn.close()


# 8. Adjust stock
@app.post("/products/{product_id}/adjust-stock", tags=["products"],
          dependencies=[Depends(require_auth)])
def adjust_stock(product_id: int, body: StockAdjust):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Product not found")
        new_qty = row["quantity"] + body.delta
        if new_qty < 0:
            raise HTTPException(status_code=400,
                                detail=f"Insufficient stock: have {row['quantity']}, delta {body.delta}")
        conn.execute("UPDATE products SET quantity = ?, updated_at = ? WHERE id = ?",
                     (new_qty, now_iso(), product_id))
        conn.commit()
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return {"product": _product_dict(row), "applied_delta": body.delta, "reason": body.reason}
    finally:
        conn.close()


# 17. Product order history
@app.get("/products/{product_id}/orders", tags=["products"],
         dependencies=[Depends(require_auth)])
def product_orders(
    product_id: int,
    include_cancelled: bool = Query(False, description="Also list cancelled orders"),
):
    conn = get_conn()
    try:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        sql = """SELECT o.id AS order_id, o.order_number, o.customer_name, o.status,
                        o.created_at, oi.quantity, oi.unit_price, oi.subtotal
                 FROM order_items oi
                 JOIN orders o ON o.id = oi.order_id
                 WHERE oi.product_id = ?"""
        if not include_cancelled:
            sql += " AND o.status != 'cancelled'"
        sql += " ORDER BY o.created_at DESC"
        rows = [dict(r) for r in conn.execute(sql, (product_id,)).fetchall()]
        return {
            "product": _product_dict(product),
            "orders_count": len(rows),
            "units_sold": sum(r["quantity"] for r in rows),
            "revenue": round(sum(r["subtotal"] for r in rows), 2),
            "items": rows,
        }
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Orders
# --------------------------------------------------------------------------- #
# 9. Create order (deducts stock)
@app.post("/orders", tags=["orders"], dependencies=[Depends(require_auth)])
def create_order(body: OrderIn):
    if not body.items:
        raise HTTPException(status_code=400, detail="Order must have at least one item")
    conn = get_conn()
    try:
        resolved = []
        total = 0.0
        for item in body.items:
            prod = conn.execute("SELECT * FROM products WHERE sku = ?", (item.sku,)).fetchone()
            if not prod:
                raise HTTPException(status_code=400, detail=f"Unknown SKU '{item.sku}'")
            if prod["quantity"] < item.quantity:
                raise HTTPException(
                    status_code=409,
                    detail=f"Not enough stock for {item.sku}: have {prod['quantity']}, need {item.quantity}",
                )
            subtotal = prod["sale_price"] * item.quantity
            total += subtotal
            resolved.append((prod, item.quantity, prod["sale_price"], subtotal))

        ts = now_iso()
        order_number = _generate_order_number(conn)
        cur = conn.execute(
            """INSERT INTO orders
            (order_number, customer_name, customer_email, customer_phone, status,
             total, currency, notes, inventory_deducted, created_at, updated_at)
            VALUES (?,?,?,?, 'accepted', ?, 'USD', ?, 1, ?, ?)""",
            (order_number, body.customer_name, body.customer_email, body.customer_phone,
             total, body.notes, ts, ts),
        )
        order_id = cur.lastrowid
        for prod, qty, unit_price, subtotal in resolved:
            conn.execute(
                """INSERT INTO order_items
                (order_id, product_id, product_name, quantity, unit_price, subtotal)
                VALUES (?,?,?,?,?,?)""",
                (order_id, prod["id"], prod["name"], qty, unit_price, subtotal),
            )
            conn.execute("UPDATE products SET quantity = quantity - ?, updated_at = ? WHERE id = ?",
                         (qty, ts, prod["id"]))
        conn.commit()
        return _order_with_items(conn, order_id)
    finally:
        conn.close()


# 10. List orders
@app.get("/orders", tags=["orders"], dependencies=[Depends(require_auth)])
def list_orders(status: Optional[str] = None, limit: int = 50, offset: int = 0):
    conn = get_conn()
    try:
        sql = "SELECT * FROM orders WHERE 1=1"
        args: list = []
        if status:
            sql += " AND status = ?"
            args.append(status)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        args += [limit, offset]
        rows = conn.execute(sql, args).fetchall()
        return {"count": len(rows), "items": [dict(r) for r in rows]}
    finally:
        conn.close()


# 16. Search orders (date range, customer, minimum total)
# Declared before /orders/{order_id} so the literal path wins over the dynamic
# one — same reason /products/low-stock sits above /products/{product_id}.
@app.get("/orders/search", tags=["orders"], dependencies=[Depends(require_auth)])
def search_orders(
    date_from: Optional[str] = Query(None, alias="from", description="Inclusive start date, YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, alias="to", description="Inclusive end date, YYYY-MM-DD"),
    customer: Optional[str] = Query(None, description="Partial match on customer name or email"),
    min_total: Optional[float] = Query(None, description="Only orders with total >= this value"),
    status: Optional[str] = Query(None, description="pending | accepted | cancelled"),
    limit: int = 50,
    offset: int = 0,
):
    for label, value in (("from", date_from), ("to", date_to)):
        if value and not _valid_date(value):
            raise HTTPException(status_code=400,
                                detail=f"'{label}' must be a date in YYYY-MM-DD format")
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="'from' must not be later than 'to'")

    conn = get_conn()
    try:
        sql = "SELECT * FROM orders WHERE 1=1"
        args: list = []
        if date_from:
            sql += " AND date(created_at) >= date(?)"
            args.append(date_from)
        if date_to:
            sql += " AND date(created_at) <= date(?)"
            args.append(date_to)
        if customer:
            sql += " AND (customer_name LIKE ? OR customer_email LIKE ?)"
            args += [f"%{customer}%", f"%{customer}%"]
        if min_total is not None:
            sql += " AND total >= ?"
            args.append(min_total)
        if status:
            sql += " AND status = ?"
            args.append(status)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        args += [limit, offset]
        rows = conn.execute(sql, args).fetchall()
        return {
            "count": len(rows),
            "filters": {"from": date_from, "to": date_to, "customer": customer,
                        "min_total": min_total, "status": status},
            "items": [dict(r) for r in rows],
        }
    finally:
        conn.close()


# 11. Get order (with items)
@app.get("/orders/{order_id}", tags=["orders"], dependencies=[Depends(require_auth)])
def get_order(order_id: int):
    conn = get_conn()
    try:
        return _order_with_items(conn, order_id)
    finally:
        conn.close()


# 12. Update order status (restocks on cancel)
@app.patch("/orders/{order_id}/status", tags=["orders"], dependencies=[Depends(require_auth)])
def update_order_status(order_id: int, body: StatusIn):
    if body.status not in ("pending", "accepted", "cancelled"):
        raise HTTPException(status_code=400, detail="status must be pending|accepted|cancelled")
    conn = get_conn()
    try:
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        ts = now_iso()
        # If cancelling an order whose stock was deducted, restock it.
        if body.status == "cancelled" and order["inventory_deducted"]:
            items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
            for it in items:
                conn.execute("UPDATE products SET quantity = quantity + ?, updated_at = ? WHERE id = ?",
                             (it["quantity"], ts, it["product_id"]))
            conn.execute("UPDATE orders SET inventory_deducted = 0 WHERE id = ?", (order_id,))
        conn.execute("UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
                     (body.status, ts, order_id))
        conn.commit()
        return _order_with_items(conn, order_id)
    finally:
        conn.close()


# 13. Customers (derived from orders)
@app.get("/customers", tags=["customers"], dependencies=[Depends(require_auth)])
def list_customers():
    conn = get_conn()
    try:
        rows = conn.execute(
            """SELECT customer_name, customer_email,
                      COUNT(*) AS orders_count, SUM(total) AS total_spent
               FROM orders
               GROUP BY customer_name, customer_email
               ORDER BY total_spent DESC"""
        ).fetchall()
        return {"count": len(rows), "items": [dict(r) for r in rows]}
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Stats
# --------------------------------------------------------------------------- #
# 14. Overview stats
@app.get("/stats/overview", tags=["stats"], dependencies=[Depends(require_auth)])
def stats_overview():
    conn = get_conn()
    try:
        products = conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
        low = conn.execute(
            "SELECT COUNT(*) AS c FROM products WHERE quantity <= minimum_stock").fetchone()["c"]
        inv_value = conn.execute(
            "SELECT COALESCE(SUM(quantity * cost_price), 0) AS v FROM products").fetchone()["v"]
        orders = conn.execute("SELECT COUNT(*) AS c FROM orders").fetchone()["c"]
        revenue = conn.execute(
            "SELECT COALESCE(SUM(total), 0) AS v FROM orders WHERE status != 'cancelled'"
        ).fetchone()["v"]
        return {
            "products": products,
            "low_stock_products": low,
            "inventory_cost_value": round(inv_value, 2),
            "orders": orders,
            "revenue": round(revenue, 2),
            "currency": "USD",
        }
    finally:
        conn.close()


# 15. Top-selling products
@app.get("/stats/top-products", tags=["stats"], dependencies=[Depends(require_auth)])
def stats_top_products(limit: int = 5):
    conn = get_conn()
    try:
        rows = conn.execute(
            """SELECT p.id, p.name, p.sku,
                      SUM(oi.quantity) AS units_sold,
                      SUM(oi.subtotal) AS revenue
               FROM order_items oi
               JOIN products p ON p.id = oi.product_id
               JOIN orders o ON o.id = oi.order_id
               WHERE o.status != 'cancelled'
               GROUP BY p.id
               ORDER BY units_sold DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return {"count": len(rows), "items": [dict(r) for r in rows]}
    finally:
        conn.close()


# 18. Sales by month
@app.get("/stats/sales-by-month", tags=["stats"], dependencies=[Depends(require_auth)])
def stats_sales_by_month(
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Only this calendar year"),
):
    conn = get_conn()
    try:
        sql = """SELECT strftime('%Y-%m', o.created_at) AS month,
                        COUNT(DISTINCT o.id) AS orders,
                        SUM(oi.quantity) AS units_sold,
                        SUM(oi.subtotal) AS revenue
                 FROM orders o
                 JOIN order_items oi ON oi.order_id = o.id
                 WHERE o.status != 'cancelled'"""
        args: list = []
        if year is not None:
            sql += " AND strftime('%Y', o.created_at) = ?"
            args.append(str(year))
        sql += " GROUP BY month ORDER BY month ASC"
        months = [
            {**dict(r), "revenue": round(r["revenue"], 2)}
            for r in conn.execute(sql, args).fetchall()
        ]
        return {
            "year": year,
            "months": months,
            "totals": {
                "orders": sum(m["orders"] for m in months),
                "units_sold": sum(m["units_sold"] for m in months),
                "revenue": round(sum(m["revenue"] for m in months), 2),
            },
        }
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _order_with_items(conn, order_id):
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    d = dict(order)
    d["items"] = [dict(i) for i in items]
    return d


if __name__ == "__main__":
    import uvicorn
    # Render and similar platforms inject $PORT; fall back to 8000 locally.
    port = int(os.getenv("PORT", "8000"))
    # Auto-reload is a local convenience: skip it wherever $PORT is provided.
    reload = os.getenv("PORT") is None
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=reload)
