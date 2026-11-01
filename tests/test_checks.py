import copy
import unittest
from collections import namedtuple

from steelframe.llm.errors import AllRoutesFailed
from steelframe.pipeline import checks, fact_checker
from tests.test_writer import good_draft, pack

Result = namedtuple("Result", "provider model")
COPYABLE = {"PIB": True, "RBI": False}


class CitationTests(unittest.TestCase):
    def test_cited_ids_handles_every_marker_style(self):
        self.assertEqual(checks.cited_ids("a [c1] b [c3, c4] c [c6-c8] d [c10; c12] e [c2 – c3]"),
                         {1, 3, 4, 6, 7, 8, 10, 12, 2})
        self.assertEqual(checks.cited_ids("no markers, just 1, 2 and c3"), set())

    def test_numbers_ignore_markers_list_numbers_and_commas(self):
        self.assertEqual(checks.numbers_in("Rs. 1,09,019 crore [c1, c2] on 31st"), {"109019", "31"})
        self.assertEqual(checks.numbers_in("1. First statement\n2. Second in 2026."), {"2026"})
        self.assertEqual(checks.numbers_in("seven States", words=True), {"7"})
        self.assertEqual(checks.numbers_in("seven States"), set())


class CodeCheckTests(unittest.TestCase):
    def test_good_draft_passes_all_three(self):
        self.assertEqual(checks.run_code_checks(good_draft(), pack(), COPYABLE), [])

    def test_quote_must_be_word_for_word_but_ignores_spacing_and_curly_quotes(self):
        draft = good_draft()
        draft["claims"][0]["quote"] = "Rs.  1,09,019   crore"
        self.assertEqual(checks.quote_check(draft, pack()), [])
        draft["claims"][0]["quote"] = "Rs. 1,09,019 lakh crore"
        self.assertEqual(len(checks.quote_check(draft, pack())), 1)
        p = pack()
        p["passages"][0]["text"] = "The ‘devolution’ was released – on time"
        draft["claims"][0]["quote"] = "The 'devolution' was released - on time"
        self.assertFalse([f for f in checks.quote_check(draft, p) if f.startswith("claim c1")])

    def test_quote_is_case_sensitive(self):
        draft = good_draft()
        draft["claims"][0]["quote"] = "rs. 1,09,019 CRORE"
        self.assertEqual(len(checks.quote_check(draft, pack())), 1)

    def test_link_check_rejects_missing_passage_and_link_only_source(self):
        draft = good_draft()
        draft["claims"][0]["passage"] = "P99"
        self.assertIn("not in the evidence pack", checks.link_check(draft, pack(), COPYABLE)[0])
        p = pack()
        p["passages"][0]["source"] = "RBI"
        self.assertEqual(len(checks.link_check(good_draft(), p, COPYABLE)), 3)

    def test_figure_check_catches_invented_numbers_everywhere(self):
        for where in ("brief", "editorial", "deep_dive", "approach", "stem", "explanation"):
            draft = good_draft()
            if where == "brief":
                draft["brief"][0] += " It is 42 per cent of the total."
            elif where in ("editorial", "deep_dive"):
                draft[where][0]["text"] += " The share is 42 per cent."
            elif where == "approach":
                draft["mains_question"]["approach"][0] = "Cite Article 280"
            elif where == "stem":
                draft["recall_questions"][0]["question"] += " (since 1951)"
            else:
                draft["recall_questions"][0]["explanation"] = "Set up in 1951."
            with self.subTest(where):
                self.assertEqual(len(checks.figure_check(draft)), 1)

    def test_rounded_or_converted_amounts_count_as_the_same_figure(self):
        draft = good_draft()
        draft["brief"][0] = "The Centre released Rs 1.09 lakh crore [c1]."      # 1,09,019 crore rounded
        draft["editorial"][0]["text"] += " About \u20b91.09 lakh crore went out."
        self.assertEqual(checks.figure_check(draft), [])
        draft["brief"][0] = "The Centre released Rs 1.2 lakh crore [c1]."       # 10% off: a different figure
        self.assertEqual(len(checks.figure_check(draft)), 1)
        draft["brief"][0] = "The Centre released Rs 1.09 crore [c1]."           # right digits, wrong unit
        self.assertEqual(len(checks.figure_check(draft)), 1)

    def test_figure_in_option_text_is_allowed(self):
        draft = good_draft()
        draft["recall_questions"][0]["options"][0] = "Article 280"
        self.assertEqual(checks.figure_check(draft), [])


class FakeRouter:
    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def complete_json(self, stage, system, user, validate=None, max_tokens=4096, exclude=()):
        self.calls.append((stage, user, exclude))
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        validate(answer)
        return answer, Result("groq", "m")


def verdicts(claim="supported", question="supported", skip=None):
    claims = [{"id": f"c{i}", "verdict": claim if i == 2 else "supported", "note": "n"} for i in (1, 2, 3)]
    return {"claims": claims, "questions": [{"n": n, "verdict": question if n == 1 else "supported", "note": "n"}
                                            for n in (1, 2, 3)]}


class FactCheckerTests(unittest.TestCase):
    def test_all_supported_passes_and_excludes_writer_provider(self):
        router = FakeRouter(verdicts())
        result = fact_checker.check_draft(router, good_draft(), pack(), COPYABLE, "gemini")
        self.assertTrue(result["passed"])
        self.assertEqual(router.calls[0][2], ("gemini",))
        self.assertEqual(result["checker"], "groq/m")

    def test_partly_unsupported_and_contradicted_all_fail(self):
        for verdict in ("partly", "unsupported", "contradicted"):
            with self.subTest(verdict):
                result = fact_checker.check_draft(FakeRouter(verdicts(claim=verdict)), good_draft(), pack(), COPYABLE, "x")
                self.assertFalse(result["passed"])
                self.assertIn(f"claim c2 is {verdict}", result["failures"][0])

    def test_bad_recall_question_fails_the_draft(self):
        result = fact_checker.check_draft(FakeRouter(verdicts(question="contradicted")), good_draft(), pack(), COPYABLE, "x")
        self.assertFalse(result["passed"])
        self.assertIn("recall question 1", result["failures"][0])

    def test_code_failure_skips_the_model_call(self):
        draft = good_draft()
        draft["claims"][0]["quote"] = "words that are not in the passage"
        router = FakeRouter()
        result = fact_checker.check_draft(router, draft, pack(), COPYABLE, "x")
        self.assertFalse(result["passed"])
        self.assertEqual(router.calls, [])

    def test_prompt_shows_passages_and_claims_but_not_the_long_text(self):
        router = FakeRouter(verdicts())
        fact_checker.check_draft(router, good_draft(), pack(), COPYABLE, "x")
        prompt = router.calls[0][1]
        self.assertIn("[P11]", prompt)
        self.assertIn("c1 (cites P11)", prompt)
        self.assertNotIn("The measure affects the States", prompt)

    def test_validator_rejects_missing_duplicate_or_unknown_verdicts(self):
        validate = fact_checker.make_validator(["c1", "c2", "c3"], 3)
        good = verdicts()
        validate(good)
        bad = []
        missing = copy.deepcopy(good); missing["claims"].pop(); bad.append(missing)
        dup = copy.deepcopy(good); dup["claims"][2]["id"] = "c1"; bad.append(dup)
        word = copy.deepcopy(good); word["claims"][0]["verdict"] = "maybe"; bad.append(word)
        noq = copy.deepcopy(good); del noq["questions"]; bad.append(noq)
        for obj in bad + [[], "x"]:
            with self.subTest(obj=str(obj)[:40]), self.assertRaises(ValueError):
                validate(obj)

    def test_outage_propagates(self):
        with self.assertRaises(AllRoutesFailed):
            fact_checker.check_draft(FakeRouter(AllRoutesFailed("fact_checker", ["down"])), good_draft(), pack(), COPYABLE, "x")


if __name__ == "__main__":
    unittest.main()
