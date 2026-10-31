"""SQLite store for development. Table shapes follow docs/knowledge-base/STORAGE_AND_RETRIEVAL.md."""
import sqlite3
from datetime import datetime, timezone

from .urls import canonical_url

SCHEMA = """
CREATE TABLE IF NOT EXISTS source_run (
    id INTEGER PRIMARY KEY,
    source_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'ok', 'failed')),
    items_found INTEGER NOT NULL DEFAULT 0,
    items_new INTEGER NOT NULL DEFAULT 0,
    items_skipped INTEGER NOT NULL DEFAULT 0,
    error TEXT
);
CREATE TABLE IF NOT EXISTS item (
    id INTEGER PRIMARY KEY,
    source_id TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    published_at TEXT,
    fetched_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS item_published_at ON item (published_at);
"""


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)

    def start_run(self, source_id):
        cursor = self.db.execute(
            "INSERT INTO source_run (source_id, started_at, status) VALUES (?, ?, 'running')",
            (source_id, now()),
        )
        self.db.commit()
        return cursor.lastrowid

    def finish_run(self, run_id, status, found=0, new=0, skipped=0, error=None):
        self.db.execute(
            "UPDATE source_run SET finished_at = ?, status = ?, items_found = ?, items_new = ?,"
            " items_skipped = ?, error = ? WHERE id = ?",
            (now(), status, found, new, skipped, error, run_id),
        )
        self.db.commit()

    def add_items(self, source_id, items):
        """Insert items that are not stored yet. Returns how many were new. Safe to repeat."""
        new = 0
        with self.db:  # one transaction: a crash leaves no half-written batch
            for item in items:
                cursor = self.db.execute(
                    "INSERT OR IGNORE INTO item (source_id, url, title, published_at, fetched_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (source_id, canonical_url(item.link), item.title, item.published_at, now()),
                )
                new += cursor.rowcount
        return new
