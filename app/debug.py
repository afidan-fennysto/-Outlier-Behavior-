"""Debug snapshot — a read-only view of the app's inner workings for last-minute review.

WHY THIS FILE EXISTS
--------------------
During a demo / judging we may want to see the live database and engine configuration without
poking at files. This module builds a structured, READ-ONLY snapshot of everything useful.

SECURITY (OWASP)
----------------
  - The debug endpoints are only registered when DEINFLUENCE_DEBUG=1 is set in the terminal.
    In a normal/production run they do not exist at all (A05 Security Misconfiguration).
  - The snapshot is read-only; it never mutates data and never exposes secrets (there are
    none - no PII, no API keys).
"""
from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict

from . import db


def debug_enabled() -> bool:
    """True when the operator opted in via the environment (toggle from the terminal)."""
    return os.environ.get("DEINFLUENCE_DEBUG", "").lower() in ("1", "true", "yes", "on")


def _table_dump(conn: sqlite3.Connection, table: str, limit: int = 500) -> Dict[str, Any]:
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]
    rows = conn.execute(f"SELECT * FROM {table} LIMIT ?", (limit,)).fetchall()
    return {
        "columns": cols,
        "row_count": conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"],
        "rows": [dict(r) for r in rows],
    }


def database_snapshot() -> Dict[str, Any]:
    """Return every table's contents (read-only) plus the DB file path."""
    db.init_db(seed=True)
    conn = sqlite3.connect(db.DB_PATH)
    conn.row_factory = sqlite3.Row
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name")]
    snapshot = {t: _table_dump(conn, t) for t in tables}
    conn.close()
    return {"db_path": str(db.DB_PATH), "tables": snapshot}


def engine_config() -> Dict[str, Any]:
    """Expose the scoring weights and thresholds so reviewers can see the inner logic."""
    from .engines import scoring, truecost
    from .ethics import DEFAMATORY_TERMS
    from .engines.defect_nlp import DEFECT_LEXICON

    return {
        "scoring_weights": {
            "quality": scoring.W_QUALITY,
            "hype": scoring.W_HYPE,
            "value": scoring.W_VALUE,
        },
        "recommendation_bands": [
            {"min_longevity": b[0], "label": b[1]} for b in scoring.RECOMMENDATION_BANDS
        ],
        "sustainable_cpw_benchmark": truecost.SUSTAINABLE_CPW_BENCHMARK,
        "defect_categories": list(DEFECT_LEXICON.keys()),
        "defect_lexicon_size": sum(len(v) for v in DEFECT_LEXICON.values()),
        "defamation_guard_terms": sorted(DEFAMATORY_TERMS),
    }


def full_snapshot() -> Dict[str, Any]:
    return {
        "debug": True,
        "env": {
            "production_mode": os.environ.get("DEINFLUENCE_ENV", "") == "production",
            "allowed_origins_overridden": bool(os.environ.get("DEINFLUENCE_ALLOWED_ORIGINS")),
        },
        "engine_config": engine_config(),
        "database": database_snapshot(),
    }
