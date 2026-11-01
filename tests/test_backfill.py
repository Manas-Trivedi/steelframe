import io
import unittest
from datetime import datetime, timedelta, timezone

from steelframe.pipeline import backfill, triage
from tests.test_daily import CONFIG, TOPICS, ScriptedRouter, good_draft, make_store, reply, rows, verdicts

SOURCES = [{"id": "PIB", "copy": True}]


def archive_store(n_archive, n_fresh=1):
    """Item 1.. are fresh (undated); the rest are dated ten days ago, inside the 29-day window."""
    store = make_store(n=n_archive + n_fresh)
    store.db.executescript(triage.SCHEMA)
    ten_days_ago = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    for item_id in range(n_fresh + 1, n_archive + n_fresh + 1):
        store.db.execute("UPDATE item SET published_at = ? WHERE id = ?", (ten_days_ago, item_id))
    return store


class BackfillTests(unittest.TestCase):
    def go(self, store, router, count, config=CONFIG, max_minutes=90):
        out = io.StringIO()
        return backfill.run(router, store, SOURCES, TOPICS, config, count, max_minutes, out), out.getvalue()

    def router(self, n):
        return ScriptedRouter(writer=[good_draft()] * n, fact_checker=[verdicts()] * n, examiner=[reply(4)] * n)

    def test_decides_only_archive_items_and_no_more_than_count(self):
        store = archive_store(3)  # item 1 is fresh, 2-4 are archive
        code, _ = self.go(store, self.router(2), count=2)
        self.assertEqual(code, 0)
        self.assertEqual(sorted(r[0] for r in rows(store, "SELECT item_id FROM editorial")), [2, 3])

    def test_no_daily_cap_applies_and_a_second_run_finds_nothing_left(self):
        store = archive_store(3)
        config = {**CONFIG, "daily_issue_cap": 0, "monthly_issue_cap": 0}
        self.assertEqual(self.go(store, self.router(3), count=10, config=config)[0], 0)
        self.assertEqual(rows(store, "SELECT COUNT(*) FROM editorial")[0][0], 3)
        code, _ = self.go(store, self.router(0), count=10, config=config)
        self.assertEqual((code, rows(store, "SELECT COUNT(*) FROM editorial")[0][0]), (0, 3))

    def test_out_of_time_defers_everything_and_exits_nonzero(self):
        router = self.router(0)
        code, out = self.go(archive_store(2), router, count=10, max_minutes=0)
        self.assertEqual((code, router.calls), (1, 0))
        self.assertIn("out of time", out)

    def test_kill_switch_stops_it_before_any_call(self):
        router = self.router(0)
        code, out = self.go(archive_store(1), router, 5, {**CONFIG, "kill_switch": True})
        self.assertEqual((code, router.calls), (0, 0))
        self.assertIn("PAUSED", out)


if __name__ == "__main__":
    unittest.main()
