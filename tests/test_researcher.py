import io
import json
import unittest
from collections import namedtuple

from steelframe.llm.errors import AllRoutesFailed
from steelframe.pipeline import documents, researcher
from steelframe.scout.feed import FeedItem
from steelframe.scout.fetch import FetchFailed, FetchRejected
from steelframe.scout.store import Store

Result = namedtuple("Result", "provider model")

PAGE = """<html><div id="PrDateTime">31 OCT 2026</div>
<p><span>The Union Government released <b>Rs 1,09,019 crore</b> as tax devolution to States.</span></p>
<p>This is an advance instalment &amp; supports capital spending.</p>
<p>******</p><div id="RelLink"><p>Footer link text that must not be read</p></div></html>"""
COPYABLE = {"PIB": True, "RBI": False}


class FakeRouter:
    def __init__(self, *actions):
        self.actions, self.prompts = list(actions), []

    def complete_json(self, stage, system, user, validate=None, max_tokens=4096):
        self.prompts.append(user)
        action = self.actions.pop(0)
        if isinstance(action, Exception):
            raise action
        if validate:
            validate(action)
        return action, Result("fake", "m")


def fetcher_for(page=PAGE, error=None):
    calls = []

    def fetch(url):
        calls.append(url)
        if error:
            raise error
        return page.encode()
    fetch.calls = calls
    return fetch


def make_store():
    store = Store(":memory:")
    store.add_items("PIB", [FeedItem("Tax devolution released to States", "https://pib.test/1", None),
                            FeedItem("Earlier devolution instalment", "https://pib.test/2", None)])
    store.add_items("RBI", [FeedItem("RBI circular on lending", "https://rbi.test/1", None)])
    documents.ensure_schema(store.db)
    store.db.executescript(researcher.SCHEMA)
    return store


def issue(item_id=1, source="PIB"):
    return {"item_id": item_id, "source_id": source, "title": "Tax devolution", "topic": "G2.FED"}


class DocumentTests(unittest.TestCase):
    def test_extracts_release_paragraphs_only(self):
        paragraphs = documents.extract_paragraphs(PAGE)
        self.assertEqual(paragraphs[0], "The Union Government released Rs 1,09,019 crore as tax devolution to States.")
        self.assertIn("advance instalment & supports", paragraphs[1])
        self.assertFalse(any("Footer" in p for p in paragraphs))

    def test_page_without_release_text_gives_nothing(self):
        self.assertEqual(documents.extract_paragraphs("<html><p>nothing here</p></html>"), [])

    def test_chunk_respects_limit_and_loses_nothing(self):
        paragraphs = ["A" * 100, "B" * 1400, "word. " * 600]
        chunks = documents.chunk(paragraphs, limit=1500)
        self.assertTrue(all(len(c) <= 1500 for c in chunks))
        self.assertEqual("".join(c.replace(" ", "") for c in chunks), "".join(p.replace(" ", "") for p in paragraphs))

    def test_chunk_splits_one_endless_sentence(self):
        self.assertEqual([len(c) for c in documents.chunk(["x" * 3200], limit=1500)], [1500, 1500, 200])

    def test_rbi_is_never_stored(self):
        store = make_store()
        with self.assertRaises(documents.NotCopyable):
            documents.load_passages(store.db, 3, COPYABLE, fetcher_for())
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM passage").fetchone()[0], 0)

    def test_second_load_reads_the_database_not_the_network(self):
        store = make_store()
        fetch = fetcher_for()
        documents.load_passages(store.db, 1, COPYABLE, fetch)
        documents.load_passages(store.db, 1, COPYABLE, fetch)
        self.assertEqual(len(fetch.calls), 1)

    def test_search_finds_titles_and_passages_and_survives_odd_queries(self):
        store = make_store()
        documents.load_passages(store.db, 1, COPYABLE, fetcher_for())
        found = documents.search(store.db, "devolution")
        self.assertEqual({row[0] for row in found["items"]}, {1, 2})
        self.assertEqual(len(found["passages"]), 1)
        for query in ('"', "AND OR NOT", "*** ((", "", "   "):
            documents.search(store.db, query)  # must not raise


class ResearchTests(unittest.TestCase):
    def test_fetch_then_done_builds_pack_from_stored_text(self):
        store = make_store()
        router = FakeRouter({"action": "done", "passages": ["P1"], "gaps": ""})
        pack = researcher.research(router, store.db, issue(), COPYABLE, fetcher_for())
        self.assertTrue(pack["complete"])
        self.assertEqual(pack["passages"][0]["url"], "https://pib.test/1")
        self.assertIn("Rs 1,09,019 crore", pack["passages"][0]["text"])
        self.assertIn("P1:", router.prompts[0])  # the model saw the passage before choosing it

    def test_invented_passage_id_makes_pack_incomplete(self):
        store = make_store()
        router = FakeRouter({"action": "done", "passages": ["P1", "P99"]})
        pack = researcher.research(router, store.db, issue(), COPYABLE, fetcher_for())
        self.assertFalse(pack["complete"])
        self.assertEqual(len(pack["passages"]), 1)
        self.assertTrue(any("P99" in p for p in pack["problems"]))

    def test_step_limit_stops_a_wandering_run(self):
        store = make_store()
        router = FakeRouter(*[{"action": "search", "query": f"q{i}"} for i in range(20)])
        pack = researcher.research(router, store.db, issue(), COPYABLE, fetcher_for(), max_steps=3)
        self.assertFalse(pack["complete"])
        self.assertEqual(len(router.prompts), 3)
        self.assertTrue(any("step limit" in p for p in pack["problems"]))

    def test_repeated_action_is_not_executed_twice(self):
        store = make_store()
        fetch = fetcher_for()
        router = FakeRouter({"action": "fetch", "item_id": 1}, {"action": "done", "passages": ["P1"]})
        researcher.research(router, store.db, issue(), COPYABLE, fetch)
        self.assertEqual(len(fetch.calls), 1)  # the model's fetch repeats the one code already did
        self.assertIn("already did this", router.prompts[1])

    def test_link_only_main_item_gives_incomplete_pack(self):
        store = make_store()
        router = FakeRouter({"action": "done", "passages": [], "gaps": "RBI"})
        pack = researcher.research(router, store.db, issue(3, "RBI"), COPYABLE, fetcher_for())
        self.assertFalse(pack["complete"])
        self.assertIn("LINK-ONLY", router.prompts[0])

    def test_fetch_errors_are_reported_not_raised(self):
        for error in (FetchRejected("HTTP 403"), FetchFailed("timeout")):
            store = make_store()
            router = FakeRouter({"action": "done", "passages": []})
            pack = researcher.research(router, store.db, issue(), COPYABLE, fetcher_for(error=error))
            self.assertFalse(pack["complete"])
            self.assertTrue(any("could not read" in p for p in pack["problems"]))

    def test_unknown_item_id_is_an_observation(self):
        store = make_store()
        router = FakeRouter({"action": "fetch", "item_id": 999}, {"action": "done", "passages": []})
        researcher.research(router, store.db, issue(), COPYABLE, fetcher_for())
        self.assertIn("no item 999", router.prompts[1])

    def test_bad_actions_are_rejected_by_the_validator(self):
        for bad in ({}, {"action": "run"}, {"action": "search"}, {"action": "search", "query": "x" * 300},
                    {"action": "fetch", "item_id": "1"}, {"action": "fetch", "item_id": True},
                    {"action": "done"}, {"action": "done", "passages": [1]}, [], "x"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                researcher.validate_action(bad)


class StageTests(unittest.TestCase):
    def kept(self, store, rows):
        store.db.executescript("CREATE TABLE IF NOT EXISTS triage (item_id INTEGER PRIMARY KEY, relevance INTEGER,"
                               " topic TEXT, ca TEXT, reason TEXT, model TEXT, triaged_at TEXT)")
        for item_id, relevance, topic in rows:
            store.db.execute("INSERT INTO triage VALUES (?, ?, ?, 'y', 'r', 'm', 't')", (item_id, relevance, topic))

    def test_select_one_per_topic_best_first_skips_done_and_link_only(self):
        store = make_store()
        self.kept(store, [(1, 3, "G2.FED"), (2, 2, "G2.FED"), (3, 3, "G3.ECON")])  # item 3 is RBI: link-only
        self.assertEqual([i["item_id"] for i in researcher.select_issues(store.db, 5, COPYABLE)], [1])
        store.db.execute("INSERT INTO evidence_pack VALUES (1, '{}', 1, 't')")
        self.assertEqual([i["item_id"] for i in researcher.select_issues(store.db, 5, COPYABLE)], [2])

    def test_stage_saves_pack_and_reports(self):
        store = make_store()
        self.kept(store, [(1, 3, "G2.FED")])
        router = FakeRouter({"action": "done", "passages": ["P1"]})
        out = io.StringIO()
        code = researcher.run_stage(router, store, COPYABLE, 3, fetcher_for(), out)
        self.assertEqual(code, 0)
        saved = json.loads(store.db.execute("SELECT pack FROM evidence_pack WHERE item_id = 1").fetchone()[0])
        self.assertTrue(saved["complete"])

    def test_stage_exits_nonzero_when_model_unreachable(self):
        store = make_store()
        self.kept(store, [(1, 3, "G2.FED")])
        router = FakeRouter(AllRoutesFailed("researcher", ["down"]))
        self.assertEqual(researcher.run_stage(router, store, COPYABLE, 3, fetcher_for(), io.StringIO()), 2)
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM evidence_pack").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
