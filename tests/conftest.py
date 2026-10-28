"""Pytest fixtures: isolate the SQLite DB to a temp file and seed it before tests.

Keeps tests deterministic and avoids touching a developer's real deinfluence.db.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _temp_db(tmp_path_factory):
    import app.db as db
    tmp = tmp_path_factory.mktemp("data") / "test.db"
    db.DB_PATH = Path(tmp)
    # Reset any thread-local connection so it reopens against the temp path.
    db._local = importlib.import_module("threading").local()
    db.init_db(seed=True)
    yield
