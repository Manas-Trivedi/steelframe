import copy
import io
import json
import unittest
from collections import namedtuple

from steelframe.llm.errors import AllRoutesFailed
from steelframe.pipeline import daily, gate
from steelframe.scout.feed import FeedItem
from steelframe.scout.store import Store
from steelframe.taxonomy import load_topics
from tests.test_checks import verdicts
from tests.test_examiner import reply
from tests.test_writer import good_draft, pack

Result = namedtuple("Result", "provider model")
TOPICS = load_topics()
COPYABLE = {"PIB": True}
CONFIG = {"kill_switch": False, "daily_issue_cap": 3, "monthly_issue_cap": 300, "backfill_per_day": 10, "backfill_days": 29, "max_attempts": 3, "sensitive_topics": ["G2.RPA"]}


class ScriptedRouter:
    """Answers each stage from its own queue. Writes the same checks the real router's validators would."""

    def __init__(self, **stages):
        self.stages = {k: list(v) for k, v in stages.items()}
        self.calls, self.prompts = 0, []
        self.routes = {s: [("groq", "m")] for s in ("writer", "fact_checker", "examiner")}
        self.quota = type("Q", (), {"allowed": lambda self, provider: True})()

    def complete_json(self, stage, system, user, validate=None, max_tokens=4096, exclude=()):
        self.calls += 1
        self.prompts.append((stage, user, exclude))
        answer = self.stages[stage].pop(0)
        if isinstance(answer, Exception):
            raise answer
        if validate:
            validate(answer)
        return answer, Result("gemini" if stage == "writer" else "groq", "m")


def bad_quote_draft():
    draft = good_draft()
    draft["claims"][0]["quote"] = "words that are nowhere in the passage"
    return draft


def make_store(topic="G2.FED", n=1):
    store = Store(":memory:")
    daily.ensure_schema(store.db)
    for i in range(1, n + 1):
        store.add_items("PIB", [FeedItem(f"Item {i}", f"https://pib.test/{i}", None)])
        p = pack()
        p["issue"].update(item_id=i, topic=topic)
        store.db.execute("INSERT INTO evidence_pack VALUES (?, ?, 1, ?)", (i, json.dumps(p), f"2026-11-01T0{i}"))
    return store


def process(router, store, item_id=1, config=CONFIG):
    pack_ = json.loads(store.db.execute("SELECT pack FROM evidence_pack WHERE item_id = ?", (item_id,)).fetchone()[0])
    return daily.process_issue(router, store.db, item_id, pack_, TOPICS, COPYABLE, config, io.StringIO())


def rows(store, sql):
    return store.db.execute(sql).fetchall()


class ProcessIssueTests(unittest.TestCase):
    def test_happy_path_publishes_in_three_calls(self):
        store, router = make_store(), ScriptedRouter(writer=[good_draft()], fact_checker=[verdicts()], examiner=[reply(4)])
        self.assertEqual(process(router, store), "published")
        self.assertEqual(router.calls, 3)
        self.assertEqual(rows(store, "SELECT status, draft_attempt FROM editorial"), [("published", 1)])
        self.assertEqual(rows(store, "SELECT attempt, decision, calls FROM review"), [(1, "publish", 3)])
        self.assertEqual(router.prompts[1][2], ("gemini",))  # checker told to avoid the Writer's provider
        self.assertEqual(router.prompts[2][2], ("gemini",))

    def test_code_failure_sends_failures_back_and_skips_model_checks(self):
        store = make_store()
        router = ScriptedRouter(writer=[bad_quote_draft(), good_draft()], fact_checker=[verdicts()], examiner=[reply(4)])
        self.assertEqual(process(router, store), "published")
        self.assertIn("claim c1: the quote is not in passage P11", router.prompts[1][1])  # second writer call
        self.assertEqual([r[0] for r in router.prompts], ["writer", "writer", "fact_checker", "examiner"])
        self.assertEqual(rows(store, "SELECT attempt, decision FROM review ORDER BY attempt"), [(1, "revise"), (2, "publish")])

    def test_low_score_goes_back_with_the_examiners_weaknesses(self):
        store = make_store()
        router = ScriptedRouter(writer=[good_draft(), good_draft()], fact_checker=[verdicts(), verdicts()],
                                examiner=[reply(2, weaknesses=("Rank the points.",)), reply(4)])
        self.assertEqual(process(router, store), "published")
        second_writer_prompt = [p for p in router.prompts if p[0] == "writer"][1][1]
        self.assertIn("examiner: Rank the points.", second_writer_prompt)

    def test_held_after_three_failed_attempts_and_never_published(self):
        store = make_store()
        router = ScriptedRouter(writer=[bad_quote_draft()] * 3)
        self.assertEqual(process(router, store), "held")
        self.assertEqual(rows(store, "SELECT status, draft_attempt FROM editorial"), [("held", 3)])
        self.assertEqual(router.calls, 3)  # three writes, no model checks spent on bad drafts

    def test_sensitive_topic_is_held_before_any_model_call(self):
        store, router = make_store(topic="G2.RPA"), ScriptedRouter()
        self.assertEqual(process(router, store), "held")
        self.assertEqual(router.calls, 0)
        self.assertIn("sensitive", rows(store, "SELECT reasons FROM editorial")[0][0])

    def test_draft_topic_on_the_sensitive_list_is_held_after_writing(self):
        store = make_store()
        draft = good_draft()
        draft["topic"] = "G2.RPA"
        router = ScriptedRouter(writer=[draft], fact_checker=[verdicts()], examiner=[reply(4)])
        self.assertEqual(process(router, store), "held")

    def test_outage_mid_issue_resumes_without_rewriting(self):
        store = make_store()
        broken = ScriptedRouter(writer=[good_draft()], fact_checker=[AllRoutesFailed("fact_checker", ["down"])])
        with self.assertRaises(AllRoutesFailed):
            process(broken, store)
        self.assertEqual(rows(store, "SELECT COUNT(*) FROM editorial")[0][0], 0)
        self.assertEqual(rows(store, "SELECT COUNT(*) FROM draft")[0][0], 1)
        resumed = ScriptedRouter(fact_checker=[verdicts()], examiner=[reply(4)])
        self.assertEqual(process(resumed, store), "published")
        self.assertEqual([p[0] for p in resumed.prompts], ["fact_checker", "examiner"])  # no second write

    def test_resume_continues_a_revision_from_its_last_attempt(self):
        store = make_store()
        first = ScriptedRouter(writer=[bad_quote_draft(), AllRoutesFailed("writer", ["down"])])
        with self.assertRaises(AllRoutesFailed):
            process(first, store)
        second = ScriptedRouter(writer=[good_draft()], fact_checker=[verdicts()], examiner=[reply(4)])
        self.assertEqual(process(second, store), "published")
        self.assertIn("claim c1", second.prompts[0][1])  # attempt 2 carries attempt 1's failures
        self.assertEqual(rows(store, "SELECT draft_attempt FROM editorial"), [(2,)])


class RunIssuesTests(unittest.TestCase):
    def run_issues(self, router, store, config=CONFIG):
        return daily.run_issues(router, store, TOPICS, COPYABLE, config, io.StringIO())

    def test_daily_cap_limits_issues(self):
        store = make_store(n=3)
        router = ScriptedRouter(writer=[good_draft()] * 3, fact_checker=[verdicts()] * 3, examiner=[reply(4)] * 3)
        self.assertEqual(self.run_issues(router, store, {**CONFIG, "daily_issue_cap": 2}), (2, 0, 0, 0))
        self.assertEqual(self.run_issues(router, store, {**CONFIG, "daily_issue_cap": 2}), (0, 0, 0, 0))  # cap used

    def age(self, store, *item_ids):
        for item_id in item_ids:
            store.db.execute("UPDATE item SET published_at = '2026-09-01T00:00:00+00:00' WHERE id = ?", (item_id,))

    def test_fresh_has_its_daily_cap_and_archive_stops_at_its_limit(self):
        store = make_store(n=4)
        self.age(store, 3, 4)  # items 3 and 4 are archive, 1 and 2 are fresh
        router = ScriptedRouter(writer=[good_draft()] * 4, fact_checker=[verdicts()] * 4, examiner=[reply(4)] * 4)
        config = {**CONFIG, "daily_issue_cap": 1}
        run = lambda lane, limit=None: daily.run_issues(router, store, TOPICS, COPYABLE, config, io.StringIO(),
                                                       lane=lane, limit=limit)
        self.assertEqual(run("fresh"), (1, 0, 0, 0))
        self.assertEqual(run("archive", 2), (2, 0, 0, 0))  # no daily cap on the archive, only its limit
        self.assertEqual(run("archive"), (0, 0, 0, 0))  # no limit given: nothing is decided
        self.assertEqual(sorted(r[0] for r in rows(store, "SELECT item_id FROM editorial")), [1, 3, 4])

    def test_archive_issues_do_not_use_up_the_fresh_daily_or_monthly_cap(self):
        store = make_store(n=3)
        self.age(store, 2, 3)
        router = ScriptedRouter(writer=[good_draft()] * 3, fact_checker=[verdicts()] * 3, examiner=[reply(4)] * 3)
        config = {**CONFIG, "daily_issue_cap": 1, "monthly_issue_cap": 1}
        daily.run_issues(router, store, TOPICS, COPYABLE, config, io.StringIO(), lane="archive", limit=2)
        self.assertEqual(daily.fresh_room(store.db, config), 1)

    def test_a_run_past_its_deadline_defers_the_rest(self):
        store = make_store(n=2)
        router = ScriptedRouter()
        result = daily.run_issues(router, store, TOPICS, COPYABLE, CONFIG, io.StringIO(), deadline=0)
        self.assertEqual((result, router.calls), ((0, 0, 0, 2), 0))

    def test_monthly_cap_stops_both_lanes(self):
        store = make_store(n=3)
        router = ScriptedRouter(writer=[good_draft()] * 3, fact_checker=[verdicts()] * 3, examiner=[reply(4)] * 3)
        config = {**CONFIG, "daily_issue_cap": 5, "monthly_issue_cap": 2}
        self.assertEqual(self.run_issues(router, store, config), (2, 0, 0, 0))
        self.assertEqual(self.run_issues(router, store, config), (0, 0, 0, 0))

    def test_no_quota_defers_instead_of_rushing(self):
        store, router = make_store(), ScriptedRouter()
        router.quota = type("Q", (), {"allowed": lambda self, provider: False})()
        self.assertEqual(self.run_issues(router, store), (0, 0, 0, 1))
        self.assertEqual(router.calls, 0)
        self.assertEqual(rows(store, "SELECT COUNT(*) FROM editorial")[0][0], 0)

    def test_one_issues_outage_does_not_stop_the_next(self):
        store = make_store(n=2)
        router = ScriptedRouter(writer=[AllRoutesFailed("writer", ["down"]), good_draft()],
                                fact_checker=[verdicts()], examiner=[reply(4)])
        self.assertEqual(self.run_issues(router, store), (1, 0, 1, 0))

    def test_two_issues_in_a_row_that_cannot_reach_a_model_stop_the_run(self):
        store = make_store(n=4)
        down = AllRoutesFailed("writer", ["gemini/m: rate limited", "groq/m: rate limited"])
        router = ScriptedRouter(writer=[down, down])
        self.assertEqual(self.run_issues(router, store), (0, 0, 2, 1))
        self.assertEqual(router.calls, 2)  # the third issue (the cap is 3) was not tried

    def test_issues_the_models_answered_badly_do_not_stop_the_run(self):
        store = make_store(n=3)
        bad = AllRoutesFailed("writer", ["gemini/m: unusable answer or outage, brief needs 3 to 5 bullets"])
        router = ScriptedRouter(writer=[bad, bad, good_draft()], fact_checker=[verdicts()], examiner=[reply(4)])
        self.assertEqual(self.run_issues(router, store), (1, 0, 2, 0))

    def test_issue_no_model_can_write_is_held_after_three_runs(self):
        store = make_store()
        unusable = ["gemini/m: unusable answer or outage, deep_dive is too short", "groq/m: unusable answer or outage, bad JSON"]
        outcomes = [self.run_issues(ScriptedRouter(writer=[AllRoutesFailed("writer", unusable)]), store) for _ in range(3)]
        self.assertEqual(outcomes, [(0, 0, 1, 0), (0, 0, 1, 0), (0, 1, 0, 0)])
        self.assertEqual(rows(store, "SELECT status FROM editorial"), [("held",)])

    def test_outage_or_quota_failures_are_never_counted_toward_a_hold(self):
        store = make_store()
        down = ["gemini/m: unusable answer or outage, boom", "groq/m: rate limited"]
        for _ in range(4):
            self.assertEqual(self.run_issues(ScriptedRouter(writer=[AllRoutesFailed("writer", down)]), store), (0, 0, 1, 0))
        self.assertEqual(rows(store, "SELECT COUNT(*) FROM editorial")[0][0], 0)

    def test_a_good_run_resets_the_stall_count(self):
        store = make_store()
        unusable = ["gemini/m: unusable answer or outage, bad"]
        for _ in range(2):
            self.run_issues(ScriptedRouter(writer=[AllRoutesFailed("writer", unusable)]), store)
        router = ScriptedRouter(writer=[good_draft()], fact_checker=[verdicts()], examiner=[reply(4)])
        self.assertEqual(self.run_issues(router, store), (1, 0, 0, 0))
        self.assertEqual(rows(store, "SELECT COUNT(*) FROM stall")[0][0], 0)

    def test_held_and_published_are_counted_apart(self):
        store = make_store(n=2)
        router = ScriptedRouter(writer=[bad_quote_draft()] * 3 + [good_draft()], fact_checker=[verdicts()], examiner=[reply(4)])
        self.assertEqual(self.run_issues(router, store), (1, 1, 0, 0))

    def test_incomplete_packs_are_never_written(self):
        store = make_store()
        store.db.execute("UPDATE evidence_pack SET complete = 0")
        router = ScriptedRouter()
        self.assertEqual(self.run_issues(router, store), (0, 0, 0, 0))
        self.assertEqual(router.calls, 0)


class RunTests(unittest.TestCase):
    def test_kill_switch_stops_everything_loudly(self):
        out = io.StringIO()
        router = ScriptedRouter()
        code = daily.run(router, Store(":memory:"), [], TOPICS, {**CONFIG, "kill_switch": True}, out)
        self.assertEqual(code, 0)
        self.assertIn("PAUSED", out.getvalue())
        self.assertEqual(router.calls, 0)


if __name__ == "__main__":
    unittest.main()
