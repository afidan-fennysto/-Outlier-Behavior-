"""Peek inside the SQLite database — see what De-Influence has stored.

Usage (from the repo root):
    python scripts/db_peek.py

Prints the DB file path and the contents of every table. Handy for the demo so you can show
stakeholders that the catalogue, preferences and wishlist really live in a database.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import DB_PATH, init_db  # noqa: E402


def main() -> None:
    init_db(seed=True)   # make sure the DB exists and is seeded
    print(f"SQLite database file:\n  {DB_PATH}\n")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]

    for t in tables:
        rows = conn.execute(f"SELECT * FROM {t}").fetchall()
        print(f"=== {t} ({len(rows)} rows) ===")
        for r in rows:
            d = {k: r[k] for k in r.keys()}
            # Trim long fields so the console stays readable.
            for k, v in d.items():
                if isinstance(v, str) and len(v) > 70:
                    d[k] = v[:67] + "..."
            print("  " + ", ".join(f"{k}={d[k]}" for k in d))
        print()


if __name__ == "__main__":
    main()
