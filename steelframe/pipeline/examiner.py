"""Examiner: score a draft against the rubric. A model from a different provider than the Writer, in a fresh context.

The model gives each dimension a 1 to 5 score and a reason. Code does the sums and the pass rules, so the model
never decides whether a draft passes. Its list of weaknesses goes back to the Writer when the draft fails.
"""
import json

from ..taxonomy import load_topics, past_questions
from . import rubric

SYSTEM = f"""You are a strict examiner scoring an editorial for UPSC Civil Services aspirants against a rubric. \
Score each dimension from 1 to 5. Be strict. Start every dimension at 3, a decent ordinary piece. Raise a score only \
if you can point to specific text that earns it. Give 5 only if nothing in that dimension could be improved, which is \
rare. Lower a score for anything missing that the rubric asks for. Do not give credit for what is not on the page. \
Judge only the text given.

Rubric:
{rubric.anchors_text()}

Notes:
- Every claim in the piece has already been checked against its source by a separate process; the result is given. \
Score accuracy on that result and on whether the sourcing is primary.
- The reader will also see, in the margin, the syllabus topic and the number of past questions on it, given below. \
Score linking on how well the text itself ties its points to that topic and to what an answer needs.
- The piece is built from a single official release. Do not penalise missing outside facts under accuracy, but do \
score evidence, judgment and exam fit on what is actually there.

Reply with JSON only:
{{"scores": {{"accuracy": {{"score": 3, "reason": "..."}}, ... all eight keys ...}}, \
"weaknesses": ["the most useful fixes, at most five, each under 25 words"]}}
Keys: {", ".join(rubric.KEYS)}. Reasons are at most 25 words."""


def validate(obj):
    scores = obj.get("scores") if isinstance(obj, dict) else None
    if not isinstance(scores, dict) or set(scores) != set(rubric.KEYS):
        raise ValueError(f"scores must have exactly the keys {rubric.KEYS}")
    for key, entry in scores.items():
        value = entry.get("score") if isinstance(entry, dict) else None
        if isinstance(value, bool) or value not in (1, 2, 3, 4, 5):
            raise ValueError(f"{key}: score must be an integer 1 to 5")
        if not isinstance(entry.get("reason"), str):
            raise ValueError(f"{key}: reason must be text")
    weaknesses = obj.get("weaknesses")
    if not isinstance(weaknesses, list) or not all(isinstance(w, str) for w in weaknesses) or len(weaknesses) > 8:
        raise ValueError("weaknesses must be a short list of text")


def build_prompt(draft, fact_check, topic_name, question_count):
    def sections(items):
        return "\n\n".join(f"## {s['heading']}\n{s['text']}" for s in items)
    claims = "\n".join(f"{c['id']}: {c['text']}" for c in draft["claims"])
    mains = draft["mains_question"]
    return (
        f"Title: {draft['title']}\nSyllabus topic: {draft['topic']} ({topic_name}); "
        f"past questions on this topic: {question_count}\n"
        f"Fact-check result: {len(draft['claims'])} claims, all supported by their source passage "
        f"(checked by {fact_check.get('checker') or 'code'}).\n\n"
        f"BRIEF\n" + "\n".join(f"- {b}" for b in draft["brief"]) + "\n\n"
        f"EDITORIAL\n{sections(draft['editorial'])}\n\nDEEP DIVE\n{sections(draft['deep_dive'])}\n\n"
        f"MAINS QUESTION\n{mains['question']}\nApproach: " + "; ".join(mains["approach"]) + "\n\n"
        f"CLAIMS\n{claims}\n")


def examine(router, draft, fact_check, writer_provider, topics=None):
    """Return {"scores": {key: int}, "reasons": {key: str}, "total": float, "passed": bool, "weaknesses": [...], "examiner": str}."""
    topics = topics or load_topics()
    names = {t["id"]: t["name"] for t in topics}
    prompt = build_prompt(draft, fact_check, names.get(draft["topic"], draft["topic"]),
                          len(past_questions(draft["topic"])))
    parsed, result = router.complete_json("examiner", SYSTEM, prompt, validate, 6000, exclude=(writer_provider,))
    scores = {k: parsed["scores"][k]["score"] for k in rubric.KEYS}
    return {"scores": scores, "reasons": {k: parsed["scores"][k]["reason"] for k in rubric.KEYS},
            "total": rubric.total(scores), "passed": rubric.passes(scores), "weaknesses": parsed["weaknesses"],
            "examiner": f"{result.provider}/{result.model}"}
