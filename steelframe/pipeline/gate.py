"""The automatic publish gate. Plain rules in code, no model.

A draft goes live only if the code checks and the Fact-checker pass, the rubric total is at least 70 with Accuracy
above 2, the topic is not on the sensitive list, and the kill switch is off. Otherwise it goes back to the Writer
with the failure list, or is held after the last attempt. A held draft is never published and never dropped.
"""
import json
from collections import namedtuple

from . import rubric

Decision = namedtuple("Decision", "action reasons")  # action: publish | revise | hold
CONFIG = "config/gate.json"


def load_config(path=CONFIG):
    with open(path) as f:
        config = json.load(f)
    for key in ("kill_switch", "daily_issue_cap", "backfill_issue_cap", "monthly_issue_cap", "max_attempts", "sensitive_topics"):
        if key not in config:
            raise ValueError(f"{path}: missing '{key}'")
    return config


def exam_failures(exam):
    if exam["passed"]:
        return []
    reasons = [f"rubric total {exam['total']} (need {rubric.PASS_TOTAL}) with accuracy {exam['scores']['accuracy']}"]
    return reasons + [f"examiner: {w}" for w in exam["weaknesses"]]


def decide(attempt, topic, code_and_fact_failures, exam, config):
    """attempt counts from 1. exam is None when the draft failed earlier checks and was not scored."""
    if config["kill_switch"]:
        return Decision("hold", ["kill switch is on"])
    if topic in config["sensitive_topics"]:
        return Decision("hold", [f"topic {topic} is on the sensitive list"])
    failures = list(code_and_fact_failures)
    if exam is not None:
        failures += exam_failures(exam)
    if not failures:
        return Decision("publish", [])
    if attempt < config["max_attempts"]:
        return Decision("revise", failures)
    return Decision("hold", failures + [f"still failing after {attempt} attempts"])
