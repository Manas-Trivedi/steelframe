import re
import unittest
from collections import namedtuple

from steelframe.pipeline import examiner, rubric
from tests.test_writer import good_draft

Result = namedtuple("Result", "provider model")


def reply(score=4, accuracy=None, weaknesses=("Add a counterargument.",)):
    scores = {k: {"score": score, "reason": "r"} for k in rubric.KEYS}
    if accuracy is not None:
        scores["accuracy"]["score"] = accuracy
    return {"scores": scores, "weaknesses": list(weaknesses)}


class FakeRouter:
    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def complete_json(self, stage, system, user, validate=None, max_tokens=4096, exclude=()):
        self.calls.append((stage, system, user, exclude))
        validate(self.answer)
        return self.answer, Result("groq", "m")


class RubricTests(unittest.TestCase):
    def test_weights_sum_to_100_and_match_the_document(self):
        self.assertEqual(sum(rubric.WEIGHTS.values()), 100)
        table = open("docs/QUALITY_RUBRIC.md", encoding="utf-8").read().split("## Dimensions and weights")[1]
        document = {name: int(w) for name, w in re.findall(r"^\| \d \| ([^|]+?) \| (\d+) \|", table, re.M)}
        ours = {name: weight for _, name, weight, *_ in rubric.DIMENSIONS}
        self.assertEqual(document, ours)

    def test_total_and_pass_rules(self):
        self.assertEqual(rubric.total({k: 5 for k in rubric.KEYS}), 100)
        self.assertEqual(rubric.total({k: 1 for k in rubric.KEYS}), 20)
        four = {k: 4 for k in rubric.KEYS}
        self.assertEqual(rubric.total(four), 80)
        self.assertTrue(rubric.passes(four))
        self.assertFalse(rubric.passes({**four, "accuracy": 2}))     # accuracy gate beats a high total
        self.assertFalse(rubric.passes({k: 3 for k in rubric.KEYS})) # 60 is below 70
        self.assertTrue(rubric.passes({**{k: 3 for k in rubric.KEYS}, "accuracy": 5, "judgment": 4, "evidence": 4}))


class ExamineTests(unittest.TestCase):
    def test_code_computes_total_and_pass_not_the_model(self):
        router = FakeRouter(reply(score=4))
        result = examiner.examine(router, good_draft(), {"checker": "g/m"}, "gemini")
        self.assertEqual((result["total"], result["passed"]), (80, True))
        self.assertEqual(router.calls[0][3], ("gemini",))
        self.assertIn("past questions on this topic", router.calls[0][2])

    def test_accuracy_floor_fails_a_high_total(self):
        result = examiner.examine(FakeRouter(reply(score=5, accuracy=2)), good_draft(), {}, "x")
        self.assertFalse(result["passed"])
        self.assertEqual(result["total"], 85)

    def test_validator_rejects_bad_answers(self):
        good = reply()
        examiner.validate(good)
        missing = reply(); del missing["scores"]["india_link"]
        extra = reply(); extra["scores"]["bonus"] = {"score": 5, "reason": "r"}
        out_of_range = reply(); out_of_range["scores"]["judgment"]["score"] = 6
        as_text = reply(); as_text["scores"]["judgment"]["score"] = "4"
        as_bool = reply(); as_bool["scores"]["judgment"]["score"] = True
        no_reason = reply(); no_reason["scores"]["judgment"]["reason"] = None
        many = reply(weaknesses=["w"] * 9)
        for bad in (missing, extra, out_of_range, as_text, as_bool, no_reason, many, [], {"scores": []}):
            with self.subTest(bad=str(bad)[:50]), self.assertRaises(ValueError):
                examiner.validate(bad)


if __name__ == "__main__":
    unittest.main()
