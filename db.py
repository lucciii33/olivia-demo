"""SQLite database: connection, schema init, and demo seed data."""
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "demo.db"))


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now_iso():
    return datetime.now(timezone.utc).isoformat()


SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sku TEXT NOT NULL UNIQUE,
    description TEXT,
    quantity INTEGER NOT NULL DEFAULT 0,
    minimum_stock INTEGER NOT NULL DEFAULT 0,
    unit TEXT NOT NULL DEFAULT 'unit',
    cost_price REAL NOT NULL DEFAULT 0,
    sale_price REAL NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'USD',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT NOT NULL UNIQUE,
    customer_name TEXT NOT NULL,
    customer_email TEXT,
    customer_phone TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    total REAL NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'USD',
    notes TEXT,
    inventory_deducted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    subtotal REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
"""

SEED_PRODUCTS = [
    # name, sku, description, qty, min_stock, unit, cost, sale
    ("Mainsail Dacron 5.2m", "SAIL-MAIN-052", "Cruising mainsail, Dacron cloth", 12, 4, "unit", 380.0, 720.0),
    ("Genoa 135% Furling", "SAIL-GEN-135", "Roller-furling genoa 135%", 8, 3, "unit", 420.0, 810.0),
    ("Spinnaker Nylon 1.5oz", "SAIL-SPIN-15", "Asymmetric spinnaker, nylon", 5, 2, "unit", 510.0, 990.0),
    ("Stainless Shackle 8mm", "HW-SHK-08", "316 stainless bow shackle", 240, 50, "unit", 3.2, 7.5),
    ("Dyneema Line 6mm", "LINE-DYN-06", "Dyneema running rigging, per meter", 60, 100, "meter", 2.1, 5.0),
    ("Winch Handle 10in", "HW-WIN-10", "Aluminium lock-in winch handle", 18, 6, "unit", 22.0, 49.0),
    ("Sail Repair Tape", "ACC-TAPE-01", "Adhesive Dacron repair tape roll", 3, 10, "box", 6.0, 14.0),
    ("Telltales Set", "ACC-TELL-01", "Set of sail trim telltales", 45, 15, "box", 1.5, 6.0),
]


def _generate_order_number(conn):
    row = conn.execute("SELECT COUNT(*) AS c FROM orders").fetchone()
    seq = (row["c"] or 0) + 1
    return f"ORD-{datetime.now().year}-{seq:04d}"


def init_db(seed=True):
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        if seed:
            existing = conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
            if existing == 0:
                ts = now_iso()
                for p in SEED_PRODUCTS:
                    conn.execute(
                        """INSERT INTO products
                        (name, sku, description, quantity, minimum_stock, unit,
                         cost_price, sale_price, currency, created_at, updated_at)
                        VALUES (?,?,?,?,?,?,?,?, 'USD', ?, ?)""",
                        (*p, ts, ts),
                    )
                conn.commit()
                _seed_orders(conn)
    finally:
        conn.close()


def _seed_orders(conn):
    """Create a couple of demo orders so stats endpoints have data."""
    demo = [
        ("Blue Marina SL", "orders@bluemarina.example", [("SAIL-MAIN-052", 2), ("HW-SHK-08", 10)]),
        ("Regatta Club", "info@regatta.example", [("SAIL-GEN-135", 1), ("ACC-TELL-01", 4)]),
    ]
    for name, email, lines in demo:
        items = []
        total = 0.0
        for sku, qty in lines:
            prod = conn.execute("SELECT * FROM products WHERE sku = ?", (sku,)).fetchone()
            if not prod:
                continue
            unit_price = prod["sale_price"]
            subtotal = unit_price * qty
            total += subtotal
            items.append((prod, qty, unit_price, subtotal))
        if not items:
            continue
        ts = now_iso()
        order_number = _generate_order_number(conn)
        cur = conn.execute(
            """INSERT INTO orders
            (order_number, customer_name, customer_email, status, total, currency,
             inventory_deducted, created_at, updated_at)
            VALUES (?,?,?, 'accepted', ?, 'USD', 1, ?, ?)""",
            (order_number, name, email, total, ts, ts),
        )
        order_id = cur.lastrowid
        for prod, qty, unit_price, subtotal in items:
            conn.execute(
                """INSERT INTO order_items
                (order_id, product_id, product_name, quantity, unit_price, subtotal)
                VALUES (?,?,?,?,?,?)""",
                (order_id, prod["id"], prod["name"], qty, unit_price, subtotal),
            )
            conn.execute(
                "UPDATE products SET quantity = quantity - ?, updated_at = ? WHERE id = ?",
                (qty, ts, prod["id"]),
            )
    conn.commit()


if __name__ == "__main__":
    init_db()
    print(f"DB initialized at {DB_PATH}")
