import io
import unittest
from collections import namedtuple

from steelframe.llm.errors import AllRoutesFailed
from steelframe.pipeline import triage
from steelframe.scout.feed import FeedItem as Item
from steelframe.scout.store import Store
from steelframe.taxonomy import load_topics, past_questions

Result = namedtuple("Result", "provider model")
TOPICS = load_topics()
IDS = {t["id"] for t in TOPICS}


def row(n, relevance=2, topic="G2.POLICY", ca="y", reason="ok"):
    return {"n": n, "relevance": relevance, "topic": topic, "ca": ca, "reason": reason}


class FakeRouter:
    """Answers each call from a list of answers; an exception in the list is raised. Runs the validator."""

    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def complete_json(self, stage, system, user, validate=None, max_tokens=4096):
        self.calls.append(user)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        if validate:
            validate(answer)
        return answer, Result("fake", "m")


def store_with(count):
    store = Store(":memory:")
    store.add_items("PIB", [Item(f"Title {i}", f"https://x.test/{i}", None) for i in range(count)])
    return store


class TaxonomyTests(unittest.TestCase):
    def test_all_65_topics_load_with_names(self):
        self.assertEqual(len(TOPICS), 65)
        self.assertTrue(all(t.get("name") for t in TOPICS))
        self.assertIn("X.OTHER", IDS)

    def test_past_questions_for_known_topic(self):
        self.assertTrue(past_questions("G2.POLICY"))


class ValidatorTests(unittest.TestCase):
    def check(self, obj, count=2):
        triage.make_validator(count, IDS)(obj)

    def test_good_answer(self):
        self.check({"items": [row(1), row(2, 0, "X.OTHER", "n")]})

    def test_rejects_each_kind_of_bad_answer(self):
        bad = [
            [],
            {"items": "x"},
            {"items": [row(1)]},                       # missing item 2
            {"items": [row(1), row(1)]},               # duplicate, 2 missing
            {"items": [row(1), row(3)]},               # number out of range
            {"items": [row(1), row(2, relevance=4)]},
            {"items": [row(1), row(2, relevance=True)]},
            {"items": [row(1), row(2, relevance="2")]},
            {"items": [row(1), row(2, topic="G9.NOPE")]},
            {"items": [row(1), row(2, ca="maybe")]},
            {"items": [row(1), {**row(2), "reason": None}]},
            {"items": [row(1), "text"]},
        ]
        for obj in bad:
            with self.subTest(obj=obj), self.assertRaises(ValueError):
                self.check(obj)


class RunTests(unittest.TestCase):
    def test_batches_of_25_and_keeps_high_relevance(self):
        store = store_with(30)
        router = FakeRouter({"items": [row(i, 3 if i == 1 else 0) for i in range(1, 26)]},
                            {"items": [row(i, 0) for i in range(1, 6)]})
        code = triage.run(router, store, TOPICS, out=io.StringIO())
        self.assertEqual(code, 0)
        self.assertEqual(len(router.calls), 2)
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM triage").fetchone()[0], 30)
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM triage WHERE relevance >= 2").fetchone()[0], 1)

    def test_rerun_does_not_repeat_finished_items(self):
        store = store_with(3)
        triage.run(FakeRouter({"items": [row(i) for i in range(1, 4)]}), store, TOPICS, out=io.StringIO())
        router = FakeRouter()
        self.assertEqual(triage.run(router, store, TOPICS, out=io.StringIO()), 0)
        self.assertEqual(router.calls, [])

    def test_failed_batch_leaves_items_for_next_run_and_exits_nonzero(self):
        store = store_with(30)
        router = FakeRouter(AllRoutesFailed("triage", ["down"]), {"items": [row(i) for i in range(1, 6)]})
        self.assertEqual(triage.run(router, store, TOPICS, out=io.StringIO()), 1)
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM triage").fetchone()[0], 5)
        self.assertEqual(len(triage.pending_items(store.db, 100)), 25)

    def test_all_batches_failing_exits_2(self):
        store = store_with(3)
        router = FakeRouter(AllRoutesFailed("triage", ["down"]))
        self.assertEqual(triage.run(router, store, TOPICS, out=io.StringIO()), 2)

    def test_nothing_to_triage_is_not_an_error(self):
        self.assertEqual(triage.run(FakeRouter(), Store(":memory:"), TOPICS, out=io.StringIO()), 0)

    def test_kept_items_carry_past_question_counts(self):
        store = store_with(1)
        triage.run(FakeRouter({"items": [row(1, 3, "G2.POLICY")]}), store, TOPICS, out=io.StringIO())
        kept = triage.kept_with_links(store.db)
        self.assertEqual(kept[0][3], "G2.POLICY")
        self.assertGreater(kept[0][5], 0)


if __name__ == "__main__":
    unittest.main()


class EvalScoreTests(unittest.TestCase):
    def test_score_counts_keep_drop_and_missed_keeps(self):
        from steelframe.pipeline.triage_eval import score
        labels = [(3, "A"), (2, "B"), (0, "C"), (1, "D")]
        preds = [(3, "A"), (1, "B"), (2, "C"), (1, "D")]
        result = score(labels, preds)
        self.assertEqual(result["missed_keeps"], 1)
        self.assertEqual(result["labelled_keeps"], 2)
        self.assertEqual(result["keep_agreement"], 0.5)
        self.assertEqual(result["within_one"], 0.75)
        self.assertEqual(result["topic_match_on_keeps"], 1.0)
