import io
import unittest

from steelframe.pipeline import backfill, triage
from tests.test_daily import COPYABLE, CONFIG, TOPICS, ScriptedRouter, good_draft, make_store, reply, rows, verdicts

SOURCES = [{"id": "PIB", "copy": True}]


def archive_store(n_archive, n_fresh=1):
    store = make_store(n=n_archive + n_fresh)
    store.db.executescript(triage.SCHEMA)
    for item_id in range(n_fresh + 1, n_archive + n_fresh + 1):
        store.db.execute("UPDATE item SET published_at = '2026-09-01T00:00:00+00:00' WHERE id = ?", (item_id,))
    return store


class BackfillTests(unittest.TestCase):
    def go(self, store, router, count, config=CONFIG):
        out = io.StringIO()
        return backfill.run(router, store, SOURCES, TOPICS, config, count, out), out.getvalue()

    def router(self, n):
        return ScriptedRouter(writer=[good_draft()] * n, fact_checker=[verdicts()] * n, examiner=[reply(4)] * n)

    def test_decides_only_archive_items_and_no_more_than_count(self):
        store = archive_store(3)  # item 1 is fresh, 2-4 are archive
        code, _ = self.go(store, self.router(2), count=2)
        self.assertEqual(code, 0)
        self.assertEqual(sorted(r[0] for r in rows(store, "SELECT item_id FROM editorial")), [2, 3])

    def test_the_lane_cap_limits_a_run_and_a_second_run_does_nothing(self):
        store = archive_store(3)
        config = {**CONFIG, "backfill_issue_cap": 1}
        self.go(store, self.router(1), count=10, config=config)
        code, out = self.go(store, self.router(0), count=10, config=config)
        self.assertEqual((code, rows(store, "SELECT COUNT(*) FROM editorial")[0][0]), (0, 1))
        self.assertIn("nothing to do", out)

    def test_kill_switch_stops_it_before_any_call(self):
        router = self.router(0)
        code, out = self.go(archive_store(1), router, 5, {**CONFIG, "kill_switch": True})
        self.assertEqual((code, router.calls), (0, 0))
        self.assertIn("PAUSED", out)


if __name__ == "__main__":
    unittest.main()
