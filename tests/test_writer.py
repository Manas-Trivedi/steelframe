import copy
import io
import json
import unittest
from collections import namedtuple

from steelframe.llm.errors import AllRoutesFailed
from steelframe.pipeline import researcher, writer
from steelframe.scout.feed import FeedItem
from steelframe.scout.store import Store
from steelframe.taxonomy import load_topics

Result = namedtuple("Result", "provider model")
TOPICS = load_topics()
IDS = {t["id"] for t in TOPICS}
FILLER = " ".join(["The measure affects the States and their planning for the year ahead."] * 12)


def good_draft():
    return {
        "title": "Tax devolution: an advance instalment for the States",
        "topic": "G2.FED",
        "claims": [
            {"id": "c1", "text": "The Centre released Rs 1,09,019 crore", "quote": "Rs. 1,09,019 crore", "passage": "P11"},
            {"id": "c2", "text": "It is an advance instalment", "quote": "additional instalment", "passage": "P11"},
            {"id": "c3", "text": "It was released on 31 October 2026", "quote": "31 st October 2026", "passage": "P11"},
        ],
        "brief": ["The Centre released Rs 1,09,019 crore [c1].", "It is an advance instalment [c2].", "Date: 31 October [c3]."],
        "editorial": [{"heading": f"Part {i}", "text": f"Rs 1,09,019 crore [c1] {FILLER}"} for i in range(1, 5)],
        "deep_dive": [{"heading": f"Section {i}", "text": f"Advance instalment [c2] on 31 October [c3]. {FILLER}"}
                      for i in range(1, 6)],
        "mains_question": {"question": "Discuss the role of tax devolution in fiscal federalism.",
                           "approach": ["Define", "Finance Commission", "Issues", "Way forward"]},
        "recall_questions": [{"question": f"Which body decides devolution, question {i}?", "options": ["A", "B", "C", "D"],
                              "answer": 1, "explanation": "Because of the Constitution."} for i in range(3)],
    }


VALIDATE = writer.make_validator({"P11"}, IDS)


class ValidatorTests(unittest.TestCase):
    def test_good_draft_passes(self):
        VALIDATE(good_draft())

    def mutated(self, change):
        draft = good_draft()
        change(draft)
        return draft

    def test_rejects_each_kind_of_bad_draft(self):
        cases = {
            "not an object": lambda d: None,
            "unknown topic": lambda d: d.update(topic="G9.NOPE"),
            "missing title": lambda d: d.update(title=" "),
            "too few claims": lambda d: d.update(claims=d["claims"][:2]),
            "claim ids out of order": lambda d: d["claims"][1].update(id="c5"),
            "quote missing": lambda d: d["claims"][0].update(quote=""),
            "passage not in pack": lambda d: d["claims"][0].update(passage="P99"),
            "passage as integer": lambda d: d["claims"][0].update(passage=11),
            "brief too short": lambda d: d.update(brief=d["brief"][:2]),
            "brief cites unknown claim": lambda d: d["brief"].__setitem__(0, "Something happened [c9]."),
            "editorial too few sections": lambda d: d.update(editorial=d["editorial"][:3]),
            "editorial too short": lambda d: d.update(editorial=[{"heading": "h", "text": "Short text here [c1] and more"}] * 4),
            "section without text": lambda d: d["deep_dive"][0].update(text=None),
            "mains approach too short": lambda d: d["mains_question"].update(approach=["a"]),
            "two recall questions": lambda d: d.update(recall_questions=d["recall_questions"][:2]),
            "three options": lambda d: d["recall_questions"][0].update(options=["A", "B", "C"]),
            "answer out of range": lambda d: d["recall_questions"][0].update(answer=4),
            "answer is a bool": lambda d: d["recall_questions"][0].update(answer=True),
        }
        for name, change in cases.items():
            with self.subTest(name):
                draft = self.mutated(change)
                if name == "not an object":
                    draft = ["x"]
                with self.assertRaises(ValueError):
                    VALIDATE(draft)


class FakeRouter:
    def __init__(self, *answers):
        self.answers, self.prompts = list(answers), []

    def complete_json(self, stage, system, user, validate=None, max_tokens=4096):
        self.prompts.append((stage, user, max_tokens))
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        validate(answer)
        return answer, Result("fake", "m")


def pack(complete=True):
    return {"issue": {"item_id": 1, "source_id": "PIB", "title": "Tax devolution", "topic": "G2.FED"},
            "passages": [{"id": 11, "item_id": 1, "url": "https://pib.test/1", "source": "PIB",
                          "text": "The Union Government has released additional instalment ... Rs. 1,09,019 crore on 31 st October 2026",
                          "fetched_at": "t"}],
            "gaps": "", "problems": [], "steps": 1, "complete": complete}


class WriteTests(unittest.TestCase):
    def test_prompt_has_passage_ids_topics_and_failures(self):
        router = FakeRouter(good_draft())
        draft, model = writer.write(router, pack(), TOPICS, failures=["claim c2: quote not found"])
        stage, prompt, max_tokens = router.prompts[0]
        self.assertEqual((stage, model), ("writer", "fake/m"))
        self.assertIn("[P11]", prompt)
        self.assertIn("G2.FED:", prompt)
        self.assertIn("claim c2: quote not found", prompt)
        self.assertGreaterEqual(max_tokens, 8000)

    def test_incomplete_pack_is_refused_before_any_call(self):
        router = FakeRouter()
        with self.assertRaises(ValueError):
            writer.write(router, pack(complete=False), TOPICS)
        self.assertEqual(router.prompts, [])


class StageTests(unittest.TestCase):
    def store(self):
        store = Store(":memory:")
        store.add_items("PIB", [FeedItem("Tax devolution", "https://pib.test/1", None)])
        store.db.executescript(researcher.SCHEMA)
        store.db.execute("INSERT INTO evidence_pack VALUES (1, ?, 1, 't')", (json.dumps(pack()),))
        store.db.execute("INSERT INTO evidence_pack VALUES (2, ?, 0, 't')", (json.dumps(pack(False)),))
        return store

    def test_writes_only_complete_packs_and_saves_draft(self):
        store = self.store()
        code = writer.run_stage(FakeRouter(good_draft()), store, TOPICS, 3, io.StringIO())
        self.assertEqual(code, 0)
        row = store.db.execute("SELECT item_id, attempt, model FROM draft").fetchall()
        self.assertEqual(row, [(1, 1, "fake/m")])

    def test_outage_exits_2_and_saves_nothing(self):
        store = self.store()
        code = writer.run_stage(FakeRouter(AllRoutesFailed("writer", ["down"])), store, TOPICS, 3, io.StringIO())
        self.assertEqual(code, 2)
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM draft").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
