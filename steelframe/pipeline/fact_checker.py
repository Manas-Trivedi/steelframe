"""Fact-checker: a model that did not write the draft reads each claim beside its passage.

It sees only the claims, the recall questions and the passages, never the Writer's reasoning or the long text.
It runs on a different provider from the Writer (the router is told to exclude the Writer's provider). Its verdicts
are advisory to the gate in one direction only: a claim marked anything but "supported" fails the draft. The code
checks in checks.py cannot be overruled by it.
"""
from .checks import run_code_checks

VERDICTS = ("supported", "partly", "unsupported", "contradicted")

SYSTEM = """You are a strict fact-checker. For each claim, decide whether the passage it cites supports it.

Verdicts:
supported = the passage states everything the claim states (same figures, names, dates, meaning)
partly = the passage supports only part of the claim, or the claim adds detail the passage does not give
unsupported = the passage does not say it
contradicted = the passage says something different

For each recall question, decide whether the marked answer is correct and supported by the claims given. Use the \
same verdicts.

Judge only from the passages and claims given. Do not use outside knowledge. A claim that merges several facts is \
"partly" unless the passage gives every one of them. Notes are at most 20 words.

Reply with JSON only: {"claims": [{"id": "c1", "verdict": "supported", "note": "..."}], \
"questions": [{"n": 1, "verdict": "supported", "note": "..."}]}
with exactly one entry per claim and one per question."""


def build_prompt(draft, pack):
    passages = "\n\n".join(f"[P{p['id']}]\n{p['text']}" for p in pack["passages"])
    claims = "\n".join(f"{c['id']} (cites {c['passage']}): {c['text']}" for c in draft["claims"])
    questions = "\n".join(
        f"{n}. {q['question']} Options: " + " | ".join(f"({i}) {o}" for i, o in enumerate(q["options"]))
        + f". Marked answer: ({q['answer']}). Explanation: {q['explanation']}"
        for n, q in enumerate(draft["recall_questions"], 1))
    return f"Passages:\n{passages}\n\nClaims:\n{claims}\n\nRecall questions (judge each against the claims above):\n{questions}"


def make_validator(claim_ids, question_count):
    def validate(obj):
        if not isinstance(obj, dict):
            raise ValueError("answer must be a JSON object")
        for key, expected in (("claims", list(claim_ids)), ("questions", list(range(1, question_count + 1)))):
            rows = obj.get(key)
            if not isinstance(rows, list):
                raise ValueError(f"missing '{key}' list")
            field = "id" if key == "claims" else "n"
            seen = []
            for row in rows:
                if not isinstance(row, dict) or row.get("verdict") not in VERDICTS:
                    raise ValueError(f"bad entry in {key}: {row!r}")
                seen.append(row.get(field))
            if sorted(map(str, seen)) != sorted(map(str, expected)):
                raise ValueError(f"{key}: expected exactly {expected}, got {seen}")
    return validate


def check_draft(router, draft, pack, copyable, writer_provider):
    """Run code checks, then the model. Returns {"passed": bool, "failures": [...], "checker": "provider/model"}.

    The model is skipped when a code check already failed: the draft goes back to the Writer either way,
    and a model call on a draft that will be rewritten wastes free quota.
    """
    failures = run_code_checks(draft, pack, copyable)
    if failures:
        return {"passed": False, "failures": failures, "checker": None}
    claim_ids = [c["id"] for c in draft["claims"]]
    verdicts, result = router.complete_json(
        "fact_checker", SYSTEM, build_prompt(draft, pack),
        make_validator(claim_ids, len(draft["recall_questions"])), 6000, exclude=(writer_provider,))
    for row in verdicts["claims"]:
        if row["verdict"] != "supported":
            failures.append(f"claim {row['id']} is {row['verdict']}: {row.get('note', '')}".strip())
    for row in verdicts["questions"]:
        if row["verdict"] != "supported":
            failures.append(f"recall question {row['n']} is {row['verdict']}: {row.get('note', '')}".strip())
    return {"passed": not failures, "failures": failures, "checker": f"{result.provider}/{result.model}"}
