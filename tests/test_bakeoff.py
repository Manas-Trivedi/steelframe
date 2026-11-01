import unittest
from collections import namedtuple

from steelframe.llm.errors import AllRoutesFailed
from steelframe.pipeline import bakeoff
from steelframe.taxonomy import load_topics
from tests.test_examiner import reply
from tests.test_writer import good_draft, pack

Result = namedtuple("Result", "provider model")


class FakeRouter:
    def __init__(self, writer_answers):
        self.routes = {"writer": [("original", "m")]}
        self.writer_answers, self.seen = list(writer_answers), []

    def complete_json(self, stage, system, user, validate=None, max_tokens=4096, exclude=()):
        self.seen.append((stage, list(self.routes["writer"]), exclude))
        if stage == "writer":
            answer = self.writer_answers.pop(0)
            if isinstance(answer, Exception):
                raise answer
            validate(answer)
            return answer, Result("p", "m")
        return reply(4), Result("groq", "m")


class BakeoffTests(unittest.TestCase):
    def run_one(self, answer):
        router = FakeRouter([answer])
        result = bakeoff.try_candidate(router, "gemini/some-model", pack(), load_topics(), {"PIB": True})
        return router, result

    def test_good_draft_is_scored_by_an_examiner_off_the_candidates_provider(self):
        router, result = self.run_one(good_draft())
        self.assertEqual((result["shape_ok"], result["code_ok"], result["total"]), (True, True, 80))
        self.assertEqual(router.seen[0][1], [("gemini", "some-model")])  # only the candidate was tried
        self.assertEqual(router.seen[1][2], ("gemini",))
        self.assertEqual(router.routes["writer"], [("original", "m")])  # route restored

    def test_bad_quote_fails_code_checks_and_is_not_scored(self):
        draft = good_draft()
        draft["claims"][0]["quote"] = "not in the passage at all"
        router, result = self.run_one(draft)
        self.assertEqual((result["shape_ok"], result["code_ok"], result["total"]), (True, False, None))
        self.assertEqual(len(router.seen), 1)

    def test_failed_call_is_recorded_and_route_restored(self):
        router, result = self.run_one(AllRoutesFailed("writer", ["down"]))
        self.assertFalse(result["shape_ok"])
        self.assertEqual(router.routes["writer"], [("original", "m")])

    def test_summary_table(self):
        table = bakeoff.summarise({"a/b": [{"shape_ok": True, "code_ok": True, "total": 80, "seconds": 10},
                                           {"shape_ok": False, "code_ok": False, "total": None, "seconds": 20}]})
        self.assertIn("| a/b | 2 | 1 | 1 | 80.0 | 15 |", table)


if __name__ == "__main__":
    unittest.main()
