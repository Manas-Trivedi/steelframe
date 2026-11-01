import unittest
from datetime import datetime, timezone

from steelframe.pipeline import lanes
from steelframe.scout.feed import FeedItem
from steelframe.scout.store import Store

NOW = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)


def store_with(*dated):
    """Items with the given published_at (None = undated, fetched now) and an editorial decided on `decided`."""
    store = Store(":memory:")
    store.db.execute("CREATE TABLE editorial (item_id INTEGER PRIMARY KEY, status TEXT, decided_at TEXT)")
    for n, (published, decided) in enumerate(dated, 1):
        store.add_items("PIB", [FeedItem(f"t{n}", f"https://x.test/{n}", published)])
        store.db.execute("INSERT INTO editorial VALUES (?, 'published', ?)", (n, decided))
    return store


class LaneTests(unittest.TestCase):
    def test_clause_splits_items_at_the_cutoff_and_rejects_unknown_lanes(self):
        self.assertEqual(lanes.clause(None), ("1 = 1", ()))
        self.assertEqual(lanes.cutoff(NOW), "2026-10-30T09:00:00+00:00")
        with self.assertRaises(ValueError):
            lanes.clause("old")

    def test_a_decided_issue_counts_in_the_lane_its_item_had_when_decided(self):
        store = store_with(("2026-11-01T18:30:00+00:00", "2026-11-02T06:00:00+00:00"),  # a day old: fresh
                           ("2026-10-10T18:30:00+00:00", "2026-11-02T06:00:00+00:00"),  # three weeks old: archive
                           (None, "2026-11-02T06:00:00+00:00"))                        # undated: fetched now, fresh
        count = lambda lane: lanes.decided_on_day(store.db, lane, NOW)
        self.assertEqual((count("fresh"), count("archive"), count(None)), (2, 1, 3))

    def test_other_days_and_months_are_not_counted(self):
        store = store_with(("2026-10-10T00:00:00+00:00", "2026-11-01T06:00:00+00:00"),
                           ("2026-10-10T00:00:00+00:00", "2026-10-31T06:00:00+00:00"))
        self.assertEqual(lanes.decided_on_day(store.db, "archive", NOW), 0)
        self.assertEqual(lanes.decided_in_month(store.db, NOW), 1)


if __name__ == "__main__":
    unittest.main()
