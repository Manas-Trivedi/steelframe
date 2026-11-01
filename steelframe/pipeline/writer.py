"""Writer: turn an evidence pack into sourced claims, three reading depths and exam questions.

The model returns one JSON object. Every claim carries an exact quote and a passage id from the pack. The three
depths are built from the same claims (they cite them as [c1], [c2], ...), so a figure cannot differ between
the brief, the editorial and the deep dive. Quote, link and figure checks run in checks.py, not here.

    python3 -m steelframe.pipeline.writer [--db data/raw/scout.sqlite] [--drafts 3]

Exit code: 0 every draft written, 1 some failed (retried next run), 2 none could be written.
"""
import argparse
import json
import logging
import re
import sys

from ..llm.errors import AllRoutesFailed
from ..scout.store import Store, now
from ..taxonomy import load_topics
from .common import build_router

log = logging.getLogger("steelframe.writer")
MARKER = re.compile(r"\[c(\d+)\]")
MAX_TOKENS = 16000  # reasoning models spend part of this thinking before the JSON starts

SCHEMA = """
CREATE TABLE IF NOT EXISTS draft (
    id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES item (id),
    attempt INTEGER NOT NULL,
    draft TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (item_id, attempt)
);
"""

SYSTEM = """You write one editorial for UPSC Civil Services aspirants (India) on the issue below, from the \
passages you are given. Your readers want to understand the issue and write a good Mains answer. Plain, exact, \
useful writing. No hype, no filler.

SOURCING (the most important rule)
- First write `claims`: every fact, figure, date, name or decision you will state. One fact per claim.
- Each claim has: id "c1", "c2", ...; text (your own words); quote (copied EXACTLY, character for character, \
from one passage; keep it short, a phrase or one sentence); passage (the id such as "P11" that holds the quote).
- Use only the passages given. Never add a fact, number or date that is not in a passage. If the passages are \
thin, write a shorter piece. Do not pad with invented background.
- In the brief, editorial and deep dive, cite claims as [c1], [c2] right after the sentence they support. Every \
number in those texts must come from a claim. The same measure carries the same figure everywhere.
- You may add analysis (why it matters, trade-offs, a view) without a claim, but never new figures or facts in it.

CONTENT
- brief: 3 to 5 bullet strings, about 120 words in all.
- editorial: 4 to 6 sections {"heading", "text"}, about 600 words in all. Cover what the measure is, what is new, \
what is weak or contested, and what should be done. Weigh the points, give the strongest counterargument, and \
say whether it is likely to work.
- deep_dive: 5 to 8 sections {"heading", "text"}, about 1,000 words in all. Add context, institutions, legal basis, \
and a Mains angle. Keep Prelims facts together in one section headed "Prelims facts".
- mains_question: {"question": "...", "approach": ["3 to 6 short points"]}, in UPSC style.
- recall_questions: exactly 3 Prelims-style questions {"question", "options": [4 strings], "answer": 0-3, \
"explanation"}. Each must be answerable from the claims.
- topic: one id from the topic list. title: at most 110 characters.

Reply with JSON only, with keys: title, topic, claims, brief, editorial, deep_dive, mains_question, recall_questions."""


def _text(value, name, minimum=1):
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise ValueError(f"{name} must be non-empty text")
    return value


def _cited(text, claim_ids, where):
    markers = {int(m) for m in MARKER.findall(text)}
    unknown = [m for m in markers if f"c{m}" not in claim_ids]
    if unknown:
        raise ValueError(f"{where} cites unknown claims {unknown}")
    return markers


def _sections(value, name, low, high, claim_ids, min_words):
    if not isinstance(value, list) or not low <= len(value) <= high:
        raise ValueError(f"{name} needs {low} to {high} sections")
    cited, words = set(), 0
    for i, section in enumerate(value, 1):
        if not isinstance(section, dict):
            raise ValueError(f"{name} section {i} must be an object")
        _text(section.get("heading"), f"{name} section {i} heading")
        body = _text(section.get("text"), f"{name} section {i} text", 20)
        words += len(body.split())
        cited |= _cited(body, claim_ids, f"{name} section {i}")
    if words < min_words:
        raise ValueError(f"{name} is too short ({words} words, need {min_words})")
    return cited


def make_validator(passage_ids, topic_ids):
    def validate(obj):
        if not isinstance(obj, dict):
            raise ValueError("draft must be a JSON object")
        title = _text(obj.get("title"), "title")
        if len(title) > 140:
            raise ValueError("title is too long")
        if obj.get("topic") not in topic_ids:
            raise ValueError(f"unknown topic {obj.get('topic')!r}")
        claims = obj.get("claims")
        if not isinstance(claims, list) or not 3 <= len(claims) <= 25:
            raise ValueError("claims needs 3 to 25 entries")
        claim_ids = set()
        for i, claim in enumerate(claims, 1):
            if not isinstance(claim, dict) or claim.get("id") != f"c{i}":
                raise ValueError(f"claim {i} must have id 'c{i}' (ids run c1, c2, ... in order)")
            _text(claim.get("text"), f"claim c{i} text", 5)
            _text(claim.get("quote"), f"claim c{i} quote", 5)
            if claim.get("passage") not in passage_ids:
                raise ValueError(f"claim c{i} cites passage {claim.get('passage')!r}, not in the pack")
            claim_ids.add(claim["id"])
        brief = obj.get("brief")
        if not isinstance(brief, list) or not 3 <= len(brief) <= 5:
            raise ValueError("brief needs 3 to 5 bullets")
        cited = set()
        for i, bullet in enumerate(brief, 1):
            cited |= _cited(_text(bullet, f"brief bullet {i}", 10), claim_ids, f"brief bullet {i}")
        cited |= _sections(obj.get("editorial"), "editorial", 4, 6, claim_ids, 200)
        cited |= _sections(obj.get("deep_dive"), "deep_dive", 5, 8, claim_ids, 350)
        mains = obj.get("mains_question")
        if not isinstance(mains, dict):
            raise ValueError("mains_question must be an object")
        _text(mains.get("question"), "mains question", 10)
        approach = mains.get("approach")
        if not isinstance(approach, list) or not 3 <= len(approach) <= 6 or not all(isinstance(a, str) and a for a in approach):
            raise ValueError("mains approach needs 3 to 6 points")
        recall = obj.get("recall_questions")
        if not isinstance(recall, list) or len(recall) != 3:
            raise ValueError("recall_questions needs exactly 3 questions")
        for i, q in enumerate(recall, 1):
            if not isinstance(q, dict):
                raise ValueError(f"recall question {i} must be an object")
            _text(q.get("question"), f"recall question {i}", 10)
            options = q.get("options")
            if not isinstance(options, list) or len(options) != 4 or not all(isinstance(o, str) and o for o in options):
                raise ValueError(f"recall question {i} needs 4 options")
            if isinstance(q.get("answer"), bool) or q.get("answer") not in (0, 1, 2, 3):
                raise ValueError(f"recall question {i} answer must be 0 to 3")
            _text(q.get("explanation"), f"recall question {i} explanation", 5)
    return validate


def build_prompt(pack, topics, failures=None):
    topic_lines = "\n".join(f"{t['id']}: {t['name']}" for t in topics)
    passages = "\n\n".join(f"[{'P' + str(p['id'])}] (source {p['source']}, {p['url']})\n{p['text']}"
                           for p in pack["passages"])
    issue = pack["issue"]
    text = (f"Issue: {issue['title']}\nSuggested topic: {issue['topic']}\n\nTopics:\n{topic_lines}\n\n"
            f"Passages:\n{passages}\n")
    if pack.get("gaps"):
        text += f"\nResearcher's note on gaps: {pack['gaps']}\n"
    if failures:
        text += ("\nYour previous draft failed these checks. Fix every one and keep the rest:\n"
                 + "\n".join(f"- {f}" for f in failures) + "\n")
    return text


def write(router, pack, topics, failures=None):
    """Return (draft, "provider/model"). Raises AllRoutesFailed. `pack` must be complete."""
    if not pack.get("complete") or not pack.get("passages"):
        raise ValueError("refusing to write from an incomplete evidence pack")
    passage_ids = {f"P{p['id']}" for p in pack["passages"]}
    draft, result = router.complete_json("writer", SYSTEM, build_prompt(pack, topics, failures),
                                         make_validator(passage_ids, {t["id"] for t in topics}), MAX_TOKENS)
    return draft, f"{result.provider}/{result.model}"


def pending_packs(db, count):
    """Complete packs with no draft yet, oldest first."""
    rows = db.execute("SELECT item_id, pack FROM evidence_pack WHERE complete = 1 AND item_id NOT IN"
                      " (SELECT item_id FROM draft) ORDER BY created_at LIMIT ?", (count,)).fetchall()
    return [(item_id, json.loads(pack)) for item_id, pack in rows]


def save_draft(db, item_id, attempt, draft, model):
    with db:
        db.execute("INSERT OR REPLACE INTO draft (item_id, attempt, draft, model, created_at) VALUES (?, ?, ?, ?, ?)",
                   (item_id, attempt, json.dumps(draft), model, now()))


def run_stage(router, store, topics, count=3, out=sys.stdout):
    store.db.executescript(SCHEMA)
    packs = pending_packs(store.db, count)
    done = failed = 0
    for item_id, pack in packs:
        try:
            draft, model = write(router, pack, topics)
        except AllRoutesFailed as error:
            failed += 1
            print(f"item {item_id}: FAILED: {error}", file=out)
            continue
        save_draft(store.db, item_id, 1, draft, model)
        done += 1
        print(f"item {item_id}: draft written by {model}: {draft['title']}", file=out)
    print(f"{done}/{len(packs)} drafts written", file=out)
    if not packs:
        return 0
    return 2 if done == 0 else (1 if failed else 0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", default="data/raw/scout.sqlite")
    parser.add_argument("--drafts", type=int, default=3)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    return run_stage(build_router(), Store(args.db), load_topics(), args.drafts)


if __name__ == "__main__":
    sys.exit(main())
