"""SQLite data layer — the single source of truth for De-Influence AI.

WHY THIS FILE EXISTS
--------------------
Earlier the catalogue lived in a hardcoded Python dict. The team asked to move to a real
database so data is stored and pulled from one place (not hardcoded). We use SQLite because
it is free, built into Python (no server, no account, no cost) and is a genuine relational
database - ideal for a prototype that must still demonstrate proper persistence.

WHAT IT STORES
--------------
  products      the analysable catalogue (seeded once from the sample data + Sample_Data.xlsx)
  reviews       each product's reviews (one-to-many)
  preferences   a single user's personalization (preferred style, favourite colour, budget)
  wishlist      favourited items + a "notify me" flag (email capture is a future feature)

SECURITY NOTES (OWASP)
----------------------
  A03 Injection: every query uses parameter binding (never string formatting of inputs).
  A01/A04 Access: single-user local prototype; no cross-user data, no auth surface.
  A09 Logging: we do not log row contents. The DB file stays on the local machine.
  PII: we deliberately do NOT store email addresses yet (wishlist email is "coming soon").
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent / "data" / "deinfluence.db"
_local = threading.local()


def _conn() -> sqlite3.Connection:
    """One connection per thread (SQLite connections are not thread-safe to share)."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _local.conn = conn
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'top',
    price REAL NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'RM',
    platform TEXT NOT NULL DEFAULT 'Uploaded',
    colour TEXT DEFAULT '',
    style TEXT DEFAULT '',
    in_stock INTEGER NOT NULL DEFAULT 1,
    search_velocity TEXT NOT NULL DEFAULT '[]',  -- JSON list
    source TEXT NOT NULL DEFAULT 'seed',          -- seed | upload | manual | ocr
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    text TEXT NOT NULL,
    rating REAL,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS preferences (
    id INTEGER PRIMARY KEY CHECK (id = 1),   -- single-row, single-user prototype
    preferred_style TEXT DEFAULT '',
    favourite_colour TEXT DEFAULT '',
    monthly_budget REAL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS wishlist (
    product_id TEXT PRIMARY KEY,
    notify_on_restock INTEGER NOT NULL DEFAULT 0,
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);
"""


def init_db(seed: bool = True) -> None:
    """Create tables, run light migrations, and (optionally) seed the catalogue once."""
    conn = _conn()
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate(conn)
    if seed and _product_count() == 0:
        _seed_catalogue()


def reset_catalogue() -> None:
    """Wipe products/reviews/wishlist and reseed - used to restore a clean demo state.

    Done in-place with SQL (no file delete) so it works even if the DB file is locked by an
    editor. Preferences are left intact.
    """
    conn = _conn()
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.execute("DELETE FROM wishlist")
    conn.execute("DELETE FROM reviews")
    conn.execute("DELETE FROM products")
    conn.commit()
    _seed_catalogue()


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns introduced after a DB may have first been created (idempotent)."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(products)")}
    if "source_url" not in cols:
        conn.execute("ALTER TABLE products ADD COLUMN source_url TEXT DEFAULT ''")
        conn.commit()


def _product_count() -> int:
    return _conn().execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]


# ---------------------------------------------------------------------------
# Seeding — the catalogue is READ from code+Excel ONCE, then lives in the DB.
# After seeding, the DB (not the dict) is the source of truth.
# ---------------------------------------------------------------------------
def _seed_catalogue() -> None:
    from .data.sample_products import SAMPLE_PRODUCTS

    for p in SAMPLE_PRODUCTS.values():
        upsert_product({
            "id": p["id"], "name": p["name"], "category": p["category"],
            "price": p["price"], "currency": p["currency"], "platform": p["platform"],
            "colour": p.get("colour", ""), "style": p.get("style", ""),
            "in_stock": 1, "search_velocity": p.get("search_velocity", []),
            "source": "seed", "source_url": p.get("source_url", ""),
        }, reviews=p.get("reviews", []))

    # Also seed a product built from the real Sample_Data.xlsx benchmark reviews, so the
    # catalogue reflects the supplied dataset rather than only synthetic items.
    try:
        from .data.benchmark import load_benchmark
        rows = load_benchmark()
        defect_reviews = [{"text": r.text, "rating": 2 if r.is_defect else 5}
                          for r in rows if r.is_defect][:8]
        if defect_reviews:
            upsert_product({
                "id": "benchmark-flagged-top",
                "name": "Benchmark Sample Top (flagged reviews)",
                "category": "top", "price": 29.90, "currency": "RM",
                "platform": "Dataset", "colour": "white", "style": "casual",
                "in_stock": 0, "search_velocity": [12, 40, 95, 150, 120, 60, 25, 10],
                "source": "seed",
            }, reviews=defect_reviews)
    except Exception:
        # Benchmark is optional; never block startup on it.
        pass


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
def upsert_product(product: Dict[str, Any], reviews: Optional[List[Dict]] = None) -> None:
    conn = _conn()
    conn.execute(
        """INSERT INTO products (id, name, category, price, currency, platform, colour,
                                 style, in_stock, search_velocity, source, source_url)
           VALUES (:id, :name, :category, :price, :currency, :platform, :colour,
                   :style, :in_stock, :search_velocity, :source, :source_url)
           ON CONFLICT(id) DO UPDATE SET
             name=excluded.name, category=excluded.category, price=excluded.price,
             currency=excluded.currency, platform=excluded.platform, colour=excluded.colour,
             style=excluded.style, in_stock=excluded.in_stock,
             search_velocity=excluded.search_velocity, source=excluded.source,
             source_url=excluded.source_url""",
        {
            "id": product["id"], "name": product["name"],
            "category": product.get("category", "top"), "price": float(product.get("price", 0)),
            "currency": product.get("currency", "RM"), "platform": product.get("platform", "Uploaded"),
            "colour": product.get("colour", ""), "style": product.get("style", ""),
            "in_stock": 1 if product.get("in_stock", 1) else 0,
            "search_velocity": json.dumps(list(product.get("search_velocity", []))),
            "source": product.get("source", "seed"),
            "source_url": product.get("source_url", ""),
        },
    )
    if reviews is not None:
        conn.execute("DELETE FROM reviews WHERE product_id = ?", (product["id"],))
        for r in reviews:
            conn.execute(
                "INSERT INTO reviews (product_id, text, rating) VALUES (?, ?, ?)",
                (product["id"], str(r.get("text", "")), r.get("rating")),
            )
    conn.commit()


def _row_to_product(row: sqlite3.Row, with_reviews: bool = True) -> Dict[str, Any]:
    product = {
        "id": row["id"], "name": row["name"], "category": row["category"],
        "price": row["price"], "currency": row["currency"], "platform": row["platform"],
        "colour": row["colour"], "style": row["style"], "in_stock": bool(row["in_stock"]),
        "search_velocity": json.loads(row["search_velocity"] or "[]"),
        "source": row["source"],
        "source_url": (row["source_url"] if "source_url" in row.keys() else "") or "",
    }
    if with_reviews:
        rev = _conn().execute(
            "SELECT text, rating FROM reviews WHERE product_id = ?", (row["id"],)
        ).fetchall()
        product["reviews"] = [{"text": r["text"], "rating": r["rating"]} for r in rev]
    return product


def list_products() -> List[Dict[str, Any]]:
    rows = _conn().execute("SELECT * FROM products ORDER BY created_at").fetchall()
    return [_row_to_product(r, with_reviews=False) for r in rows]


def get_product(product_id: str) -> Optional[Dict[str, Any]]:
    row = _conn().execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return _row_to_product(row) if row else None


def find_by_source_url(url: str) -> Optional[Dict[str, Any]]:
    """Exact-match a demo link to a seeded product (parameter-bound, A03-safe)."""
    row = _conn().execute(
        "SELECT * FROM products WHERE source_url = ? AND source_url != ''", (url,)
    ).fetchone()
    return _row_to_product(row) if row else None


def pick_product_by_index(index: int) -> Optional[Dict[str, Any]]:
    """Deterministic fallback: pick the Nth catalogue product (stable for a given link)."""
    rows = _conn().execute("SELECT * FROM products ORDER BY created_at").fetchall()
    if not rows:
        return None
    return _row_to_product(rows[index % len(rows)])


def alternative_candidates(category: str, exclude_id: str) -> List[Dict[str, Any]]:
    """In-stock catalogue items that could be a better alternative (same category first).

    Returns full products (with reviews) so the caller can score them. Parameter-bound (A03).
    """
    rows = _conn().execute(
        "SELECT * FROM products WHERE id != ? AND in_stock = 1 ORDER BY created_at",
        (exclude_id or "",),
    ).fetchall()
    products = [_row_to_product(r) for r in rows]
    same = [p for p in products if p["category"] == category]
    # Prefer same-category candidates; fall back to any in-stock item.
    return same or products


def delete_product(product_id: str) -> bool:
    conn = _conn()
    cur = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Preferences (single-user)
# ---------------------------------------------------------------------------
def get_preferences() -> Dict[str, Any]:
    row = _conn().execute("SELECT * FROM preferences WHERE id = 1").fetchone()
    if not row:
        return {"preferred_style": "", "favourite_colour": "", "monthly_budget": 0.0}
    return {
        "preferred_style": row["preferred_style"],
        "favourite_colour": row["favourite_colour"],
        "monthly_budget": row["monthly_budget"],
    }


def set_preferences(preferred_style: str, favourite_colour: str, monthly_budget: float) -> Dict[str, Any]:
    conn = _conn()
    conn.execute(
        """INSERT INTO preferences (id, preferred_style, favourite_colour, monthly_budget, updated_at)
           VALUES (1, ?, ?, ?, datetime('now'))
           ON CONFLICT(id) DO UPDATE SET
             preferred_style=excluded.preferred_style,
             favourite_colour=excluded.favourite_colour,
             monthly_budget=excluded.monthly_budget,
             updated_at=datetime('now')""",
        (preferred_style, favourite_colour, float(monthly_budget)),
    )
    conn.commit()
    return get_preferences()


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------
def add_to_wishlist(product_id: str, notify_on_restock: bool = False) -> bool:
    if not get_product(product_id):
        return False
    conn = _conn()
    conn.execute(
        """INSERT INTO wishlist (product_id, notify_on_restock) VALUES (?, ?)
           ON CONFLICT(product_id) DO UPDATE SET notify_on_restock=excluded.notify_on_restock""",
        (product_id, 1 if notify_on_restock else 0),
    )
    conn.commit()
    return True


def remove_from_wishlist(product_id: str) -> bool:
    conn = _conn()
    cur = conn.execute("DELETE FROM wishlist WHERE product_id = ?", (product_id,))
    conn.commit()
    return cur.rowcount > 0


def list_wishlist() -> List[Dict[str, Any]]:
    rows = _conn().execute(
        """SELECT w.product_id, w.notify_on_restock, w.added_at, p.in_stock
           FROM wishlist w JOIN products p ON p.id = w.product_id
           ORDER BY w.added_at DESC"""
    ).fetchall()
    out = []
    for r in rows:
        product = get_product(r["product_id"])
        if product:
            out.append({
                "product": product,
                "notify_on_restock": bool(r["notify_on_restock"]),
                "in_stock": bool(r["in_stock"]),
                "added_at": r["added_at"],
            })
    return out
