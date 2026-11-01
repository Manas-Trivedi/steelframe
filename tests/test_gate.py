import unittest

from steelframe.pipeline import gate

CONFIG = {"kill_switch": False, "daily_issue_cap": 3, "backfill_issue_cap": 7, "monthly_issue_cap": 300, "max_attempts": 3, "sensitive_topics": ["G2.RPA"]}
PASSING = {"passed": True, "total": 88, "scores": {"accuracy": 5}, "weaknesses": ["add data"]}
FAILING = {"passed": False, "total": 61, "scores": {"accuracy": 4}, "weaknesses": ["rank the points"]}


class GateTests(unittest.TestCase):
    def test_publishes_only_when_everything_passes(self):
        self.assertEqual(gate.decide(1, "G2.FED", [], PASSING, CONFIG).action, "publish")

    def test_each_failure_kind_blocks_publishing(self):
        for failures, exam in (( ["claim c1: quote not found"], None), (["claim c2 is partly supported"], None),
                               ([], FAILING)):
            with self.subTest(failures=failures):
                decision = gate.decide(1, "G2.FED", failures, exam, CONFIG)
                self.assertEqual(decision.action, "revise")
                self.assertTrue(decision.reasons)

    def test_failing_exam_reasons_carry_the_weaknesses(self):
        reasons = gate.decide(1, "G2.FED", [], FAILING, CONFIG).reasons
        self.assertIn("rubric total 61 (need 70) with accuracy 4", reasons[0])
        self.assertIn("examiner: rank the points", reasons)

    def test_accuracy_floor_blocks_a_high_total(self):
        exam = {"passed": False, "total": 85, "scores": {"accuracy": 2}, "weaknesses": []}
        self.assertEqual(gate.decide(1, "G2.FED", [], exam, CONFIG).action, "revise")

    def test_held_after_the_last_attempt(self):
        self.assertEqual(gate.decide(2, "G2.FED", ["x"], None, CONFIG).action, "revise")
        decision = gate.decide(3, "G2.FED", ["x"], None, CONFIG)
        self.assertEqual(decision.action, "hold")
        self.assertIn("after 3 attempts", decision.reasons[-1])

    def test_sensitive_topic_and_kill_switch_hold_at_once(self):
        self.assertEqual(gate.decide(1, "G2.RPA", [], PASSING, CONFIG).action, "hold")
        self.assertEqual(gate.decide(1, "G2.FED", [], PASSING, {**CONFIG, "kill_switch": True}).action, "hold")

    def test_real_config_loads_and_lists_valid_topics(self):
        from steelframe.taxonomy import load_topics
        config = gate.load_config()
        ids = {t["id"] for t in load_topics()}
        self.assertTrue(set(config["sensitive_topics"]) <= ids)
        self.assertFalse(config["kill_switch"])

    def test_config_missing_a_key_is_an_error(self):
        import json, os, tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"kill_switch": False}, f)
        self.addCleanup(os.remove, f.name)
        with self.assertRaises(ValueError):
            gate.load_config(f.name)


if __name__ == "__main__":
    unittest.main()
