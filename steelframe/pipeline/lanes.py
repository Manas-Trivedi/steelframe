"""Two lanes of issues: fresh (an item from the last few days) and archive (older, written by the backfill).

The lanes have separate daily caps so the backfill can never take the day's news slot. One monthly cap covers both.
An item's date is its source date, or the time Scout fetched it when the source gives none (the PIB feed).
"""
from datetime import datetime, timedelta, timezone

from ..scout.feed import IST

FRESH_DAYS = 3
ITEM_DATE = "COALESCE(i.published_at, i.fetched_at)"


def cutoff(now=None):
    """Items dated at or after this are fresh. ISO strings in UTC compare correctly as text."""
    return ((now or datetime.now(timezone.utc)) - timedelta(days=FRESH_DAYS)).isoformat()


def clause(lane):
    """(SQL, params) that keeps only items of `lane` ("fresh" or "archive"; None keeps all). Items are aliased `i`."""
    if lane is None:
        return "1 = 1", ()
    if lane not in ("fresh", "archive"):
        raise ValueError(f"unknown lane {lane!r}")
    return f"{ITEM_DATE} {'>=' if lane == 'fresh' else '<'} ?", (cutoff(),)


def decided_on_day(db, lane=None, now=None):
    """Issues decided (published or held) today in UTC, in the lane. Held ones used quota, so they count."""
    now = now or datetime.now(timezone.utc)
    return _decided(db, lane, now.strftime("%Y-%m-%d"))


def decided_in_month(db, lane=None, now=None):
    now = now or datetime.now(timezone.utc)
    return _decided(db, lane, now.strftime("%Y-%m"))


def since(days, now=None):
    """Items dated at or after this are within `days` days back."""
    return ((now or datetime.now(timezone.utc)) - timedelta(days=days)).isoformat()


def source_day(published_at, fetched_at):
    """The Indian calendar day of an item's source date (its fetch time when the source gives none)."""
    return datetime.fromisoformat(published_at or fetched_at).astimezone(IST).strftime("%Y-%m-%d")


def _decided(db, lane, prefix):
    """The lane of a decided issue is judged by its item's age when it was decided, not today."""
    sql = "SELECT COUNT(*) FROM editorial e JOIN item i ON i.id = e.item_id WHERE e.decided_at LIKE ?"
    if lane is not None:
        item_day = f"replace(substr({ITEM_DATE}, 1, 19), 'T', ' ')"  # same text form as SQLite's datetime()
        sql += f" AND {item_day} {'>=' if lane == 'fresh' else '<'} datetime(e.decided_at, '-{FRESH_DAYS} days')"
    return db.execute(sql, (prefix + "%",)).fetchone()[0]
