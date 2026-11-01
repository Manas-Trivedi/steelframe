import io
import json
import random
import unittest
from collections import namedtuple
from datetime import date

from steelframe.llm.errors import AllRoutesFailed
from steelframe.ops import audit, corrections
from steelframe.pipeline import daily
from steelframe.scout.store import Store
from tests.test_checks import verdicts
from tests.test_site import SITE, TOPICS, make_store, seed
from tests.test_writer import good_draft

Result = namedtuple("Result", "provider model")
TODAY = date(2026, 11, 1)


class FakeRouter:
    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def complete_json(self, stage, system, user, validate=None, max_tokens=4096, exclude=()):
        self.calls.append(exclude)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        validate(answer)
        return answer, Result("openrouter", "m")


def seeded(n=1):
    store = make_store()
    for i in range(1, n + 1):
        seed(store, i, "published", title=f"Piece {i}")
    return store


class CorrectionTests(unittest.TestCase):
    def test_correction_needs_a_published_piece_and_text(self):
        store = make_store()
        seed(store, 1, "held")
        with self.assertRaises(ValueError):
            corrections.add_correction(store.db, 1, "x")
        with self.assertRaises(ValueError):
            corrections.add_correction(store.db, 99, "x")
        seed(store, 2, "published")
        with self.assertRaises(ValueError):
            corrections.add_correction(store.db, 2, "   ")
        corrections.add_correction(store.db, 2, "The figure was wrong.")
        self.assertEqual(store.db.execute("SELECT item_id, text FROM correction").fetchall(), [(2, "The figure was wrong.")])

    def test_unpublish_holds_the_piece_and_leaves_a_dated_note(self):
        store = seeded()
        corrections.unpublish(store.db, 1, 'wrong "year"')
        status, reasons = store.db.execute("SELECT status, reasons FROM editorial").fetchone()
        self.assertEqual(status, "held")
        self.assertEqual(json.loads(reasons), ['unpublished: wrong "year"'])
        self.assertIn("Taken down", store.db.execute("SELECT text FROM correction").fetchone()[0])
        with self.assertRaises(ValueError):
            corrections.unpublish(store.db, 1, "again")  # no longer published

    def test_requeue_wipes_a_held_issue_so_it_runs_again_and_refuses_others(self):
        store = make_store()
        seed(store, 1, "held")
        seed(store, 2, "published")
        corrections.requeue(store.db, 1)
        for table in ("editorial", "draft"):
            self.assertEqual(store.db.execute(f"SELECT COUNT(*) FROM {table} WHERE item_id = 1").fetchone()[0], 0)
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM evidence_pack WHERE item_id = 1").fetchone()[0], 1)
        for bad in (2, 99, 1):
            with self.assertRaises(ValueError):
                corrections.requeue(store.db, bad)

    def test_pause_start_is_idempotent_and_clears(self):
        store = make_store()
        self.assertIsNone(corrections.active_pause(store.db))
        corrections.start_pause(store.db, "r1")
        corrections.start_pause(store.db, "r2")
        self.assertEqual(corrections.active_pause(store.db), "r1")
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM pause").fetchone()[0], 1)
        corrections.clear_pause(store.db)
        self.assertIsNone(corrections.active_pause(store.db))

    def test_site_lists_takedowns_without_a_link(self):
        import os, tempfile, shutil
        from steelframe.site import build
        store = seeded(2)
        corrections.unpublish(store.db, 1, "bad source")
        out = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, out)
        build.build(store.db, out, SITE, TOPICS, links={})
        page = open(os.path.join(out, "corrections.html"), encoding="utf-8").read()
        self.assertTrue("(taken down)" in page and "Taken down: bad source" in page)
        self.assertFalse("p/2026-11-01-1-" in page)


class AuditTests(unittest.TestCase):
    def run_audit(self, router, store, **kw):
        return audit.run_audit(router, store.db, {"PIB": True}, rng=random.Random(1), today=TODAY, out=io.StringIO(), **kw)

    def test_clean_audit_records_and_does_not_pause(self):
        store, router = seeded(), FakeRouter(verdicts())
        self.assertEqual(self.run_audit(router, store), 0)
        self.assertEqual(store.db.execute("SELECT claims, unsupported, contradicted FROM audit").fetchone(), (3, 0, 0))
        self.assertIsNone(corrections.active_pause(store.db))
        self.assertIn("g", router.calls[0])  # the writer's provider ("g/m") is excluded

    def test_contradicted_claim_pauses_publishing(self):
        store, router = seeded(), FakeRouter(verdicts(claim="contradicted"))
        self.assertEqual(self.run_audit(router, store), 1)
        self.assertIn("contradicted", corrections.active_pause(store.db))

    def test_unsupported_rate_over_five_percent_pauses_but_under_does_not(self):
        self.assertIsNone(audit.alarm_reason(100, 5, 0))
        self.assertIn("6 of 100", audit.alarm_reason(100, 6, 0))
        self.assertIsNone(audit.alarm_reason(0, 0, 0))
        self.assertIn("1 contradicted", audit.alarm_reason(100, 1, 1))

    def test_code_failure_counts_without_a_model_call(self):
        store = seeded()
        draft = good_draft()
        draft["claims"][0]["quote"] = "not in the passage"
        store.db.execute("UPDATE draft SET draft = ?", (json.dumps(draft),))
        router = FakeRouter()
        self.assertEqual(self.run_audit(router, store), 1)
        self.assertEqual(router.calls, [])
        self.assertEqual(store.db.execute("SELECT unsupported FROM audit").fetchone()[0], 1)

    def test_old_audits_fall_out_of_the_window(self):
        store = seeded()
        audit.ensure_schema(store.db)
        store.db.execute("INSERT INTO audit (item_id, audited_at, claims, unsupported, contradicted, failures)"
                         " VALUES (1, '2026-09-01T00:00:00', 10, 10, 1, '[]')")
        self.assertEqual(audit.window_stats(store.db, TODAY), (0, 0, 0))

    def test_outage_returns_2_and_records_nothing(self):
        store = seeded()
        router = FakeRouter(AllRoutesFailed("fact_checker", ["a"]), AllRoutesFailed("fact_checker", ["b"]))
        self.assertEqual(self.run_audit(router, store), 2)
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0], 0)

    def test_nothing_published_is_fine(self):
        self.assertEqual(self.run_audit(FakeRouter(), make_store()), 0)

    def test_sample_never_exceeds_the_published_count(self):
        store, router = seeded(2), FakeRouter(verdicts(), verdicts(), verdicts())
        self.run_audit(router, store, sample=5)
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0], 2)


class PausedRunTests(unittest.TestCase):
    def test_daily_run_does_nothing_while_the_alarm_is_on(self):
        store = make_store()
        corrections.start_pause(store.db, "1 contradicted claim")
        out = io.StringIO()
        router = FakeRouter()
        code = daily.run(router, store, [], TOPICS, {"kill_switch": False, "daily_issue_cap": 3, "max_attempts": 3,
                                                      "sensitive_topics": []}, out)
        self.assertEqual(code, 1)
        self.assertIn("PAUSED by the audit alarm", out.getvalue())
        self.assertEqual(router.calls, [])


if __name__ == "__main__":
    unittest.main()
