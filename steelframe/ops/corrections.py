"""Visible, dated corrections, and the pause switch that the audit alarm sets.

    python3 -m steelframe.ops.corrections add ITEM_ID "what was wrong and what is right"
    python3 -m steelframe.ops.corrections list
    python3 -m steelframe.ops.corrections requeue ITEM_ID               # retry a held issue from scratch
    python3 -m steelframe.ops.corrections unpublish ITEM_ID "reason"    # take a piece down and say why

Nothing is changed silently: a correction is stored with its date, shown at the top of the piece and listed on the
corrections page. An unpublished piece leaves the site on the next build and keeps a row saying why.
"""
import argparse
import json
import sys

from ..scout.store import Store, now

SCHEMA = """
CREATE TABLE IF NOT EXISTS correction (
    id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES item (id),
    noted_at TEXT NOT NULL,
    text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pause (
    id INTEGER PRIMARY KEY,
    reason TEXT NOT NULL,
    started_at TEXT NOT NULL,
    cleared_at TEXT
);
"""


def ensure_schema(db):
    db.executescript(SCHEMA)


def _published(db, item_id):
    row = db.execute("SELECT status FROM editorial WHERE item_id = ?", (item_id,)).fetchone()
    if row is None:
        raise ValueError(f"item {item_id} has no editorial")
    if row[0] != "published":
        raise ValueError(f"item {item_id} is {row[0]}, not published")


def add_correction(db, item_id, text):
    ensure_schema(db)
    _published(db, item_id)
    if not text.strip():
        raise ValueError("a correction needs text")
    with db:
        db.execute("INSERT INTO correction (item_id, noted_at, text) VALUES (?, ?, ?)", (item_id, now(), text.strip()))


def unpublish(db, item_id, reason):
    """Mark the piece held, with the reason, and record it as a correction so the page says what happened."""
    ensure_schema(db)
    _published(db, item_id)
    if not reason.strip():
        raise ValueError("unpublishing needs a reason")
    with db:
        db.execute("UPDATE editorial SET status = 'held', reasons = ? WHERE item_id = ?",
                   (json.dumps([f"unpublished: {reason.strip()}"]), item_id))
        db.execute("INSERT INTO correction (item_id, noted_at, text) VALUES (?, ?, ?)",
                   (item_id, now(), f"Taken down: {reason.strip()}"))


def requeue(db, item_id):
    """Give a held issue a fresh start: forget its drafts and reviews so the next daily run writes it again.

    Only a held issue can be requeued. A published one needs a correction or a takedown instead.
    """
    ensure_schema(db)
    row = db.execute("SELECT status FROM editorial WHERE item_id = ?", (item_id,)).fetchone()
    if row is None or row[0] != "held":
        raise ValueError(f"item {item_id} is not held")
    with db:
        for table in ("review", "draft", "editorial"):
            db.execute(f"DELETE FROM {table} WHERE item_id = ?", (item_id,))


def start_pause(db, reason):
    ensure_schema(db)
    if active_pause(db) is None:
        with db:
            db.execute("INSERT INTO pause (reason, started_at) VALUES (?, ?)", (reason, now()))


def active_pause(db):
    ensure_schema(db)
    row = db.execute("SELECT reason FROM pause WHERE cleared_at IS NULL ORDER BY id DESC LIMIT 1").fetchone()
    return row[0] if row else None


def clear_pause(db):
    ensure_schema(db)
    with db:
        db.execute("UPDATE pause SET cleared_at = ? WHERE cleared_at IS NULL", (now(),))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", default="data/raw/scout.sqlite")
    sub = parser.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add"); add.add_argument("item_id", type=int); add.add_argument("text")
    down = sub.add_parser("unpublish"); down.add_argument("item_id", type=int); down.add_argument("reason")
    again = sub.add_parser("requeue"); again.add_argument("item_id", type=int)
    sub.add_parser("list")
    args = parser.parse_args(argv)
    db = Store(args.db).db
    try:
        if args.cmd == "add":
            add_correction(db, args.item_id, args.text)
        elif args.cmd == "unpublish":
            unpublish(db, args.item_id, args.reason)
        elif args.cmd == "requeue":
            requeue(db, args.item_id)
        else:
            ensure_schema(db)
            for row in db.execute("SELECT item_id, noted_at, text FROM correction ORDER BY noted_at"):
                print(*row, sep="  ")
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
