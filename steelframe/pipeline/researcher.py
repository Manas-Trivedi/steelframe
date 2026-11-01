"""Researcher: a bounded agent that gathers the evidence pack for one issue.

The model picks the next action (search, fetch, done) as JSON. Code runs the action, so the model never
touches the network or the database, and a step limit stops a wandering run. The pack holds verbatim stored
passages only, so the later quote check can compare a claim's quote with the exact text.

    python3 -m steelframe.pipeline.researcher [--db data/raw/scout.sqlite] [--issues 3]

Exit code: 0 every pack complete, 1 some pack incomplete or failed, 2 nothing could be researched.
"""
import argparse
import json
import logging
import sys

from ..llm.errors import AllRoutesFailed
from ..scout.fetch import FetchFailed, FetchRejected
from ..scout.store import Store, now
from ..taxonomy import past_questions
from . import documents
from .common import build_router
from .triage import KEEP_AT

log = logging.getLogger("steelframe.researcher")
MAX_STEPS = 6
SEEN_CHARS = 300  # how much of each passage the model sees while choosing; the pack keeps the full text

SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence_pack (
    item_id INTEGER PRIMARY KEY REFERENCES item (id),
    pack TEXT NOT NULL,
    complete INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
"""

SYSTEM = """You are the researcher for an editorial about one Indian government release, written for UPSC \
Civil Services aspirants. Collect the exact passages the editorial will rely on. You do not write it.

Each turn, reply with ONE JSON action:
{"action": "search", "query": "a few key words"}      look through stored release titles and passages
{"action": "fetch", "item_id": 12}                    read a stored item's full text (split into passages P<number>)
{"action": "done", "passages": ["P3", "P7"], "gaps": "what is missing, or empty"}   finish

Rules:
- The main item has already been read for you (its passages are shown). Search for earlier related
  releases (background, earlier figures) only if they would help; otherwise finish at once.
- Choose only passages that state facts, figures, dates, decisions or quotes about the issue.
- Use only passage ids you were shown. Never invent a passage, figure or source.
- Items marked LINK-ONLY cannot be read. Do not fetch them; mention them in gaps.
- Finish within the step limit. If the main item cannot be read, finish with an empty list and say why."""


def validate_action(obj):
    if not isinstance(obj, dict):
        raise ValueError("action must be a JSON object")
    action = obj.get("action")
    if action == "search":
        query = obj.get("query")
        if not isinstance(query, str) or not query.strip() or len(query) > 200:
            raise ValueError("search needs a short non-empty query")
    elif action == "fetch":
        if not isinstance(obj.get("item_id"), int) or isinstance(obj.get("item_id"), bool):
            raise ValueError("fetch needs an integer item_id")
    elif action == "done":
        passages = obj.get("passages")
        if not isinstance(passages, list) or not all(isinstance(p, str) for p in passages):
            raise ValueError("done needs a list of passage ids")
        if not isinstance(obj.get("gaps", ""), str):
            raise ValueError("gaps must be text")
    else:
        raise ValueError(f"unknown action {action!r}")


def _passage_id(text):
    text = text.strip().upper()
    return int(text[1:]) if text.startswith("P") and text[1:].isdigit() else None


class Run:
    """State of one issue's research."""

    def __init__(self, db, issue, copyable, fetcher):
        self.db, self.issue, self.copyable, self.fetcher = db, issue, copyable, fetcher
        self.shown = {}      # passage id -> (item_id, text) the model has been shown
        self.log = []        # observations, in order
        self.problems = []
        self.done_actions = set()

    def observe(self, action):
        key = json.dumps(action, sort_keys=True)
        if key in self.done_actions:
            return "You already did this. Do something else, or finish with done."
        self.done_actions.add(key)
        if action["action"] == "search":
            return self._search(action["query"])
        return self._fetch(action["item_id"])

    def _search(self, query):
        found = documents.search(self.db, query)
        lines = [f"item {i} [{'LINK-ONLY' if not self.copyable.get(src, False) else src}]: {title}"
                 for i, src, title in found["items"]]
        lines += [f"P{pid} (item {item}): {snippet}" for pid, item, snippet in found["passages"]]
        for pid, item, _ in found["passages"]:
            text = self.db.execute("SELECT text FROM passage WHERE id = ?", (pid,)).fetchone()[0]
            self.shown[pid] = (item, text)
        return "\n".join(lines) or "No results."

    def _fetch(self, item_id):
        try:
            passages = documents.load_passages(self.db, item_id, self.copyable, self.fetcher)
        except KeyError:
            return f"There is no item {item_id}."
        except documents.NotCopyable as error:
            self.problems.append(f"item {item_id}: {error}")
            return f"LINK-ONLY: {error}"
        except (documents.NoText, FetchRejected, FetchFailed) as error:
            self.problems.append(f"item {item_id}: could not read: {error}")
            return f"Could not read it: {error}"
        for pid, text in passages:
            self.shown[pid] = (item_id, text)
        return "\n".join(f"P{pid}: {text[:SEEN_CHARS]}" for pid, text in passages[:12])

    def render(self, step):
        head = (f"Issue: item {self.issue['item_id']} [{self.issue['source_id']}]: {self.issue['title']}\n"
                f"Syllabus topic: {self.issue['topic']}\nStep {step} of {MAX_STEPS}.\n")
        return head + "\n".join(self.log)


def research(router, db, issue, copyable, fetcher=documents.fetch, max_steps=MAX_STEPS):
    """Return the evidence pack for one issue. Raises AllRoutesFailed if the model is unreachable."""
    run = Run(db, issue, copyable, fetcher)
    chosen, gaps, finished = [], "", False
    first = {"action": "fetch", "item_id": issue["item_id"]}  # always needed, so code does it, not the model
    run.log.append(f"> {json.dumps(first)}\n{run.observe(first)}")
    for step in range(1, max_steps + 1):
        action, _ = router.complete_json("researcher", SYSTEM, run.render(step), validate_action, max_tokens=4096)
        if action["action"] == "done":
            chosen, gaps, finished = action["passages"], action.get("gaps", ""), True
            break
        observation = run.observe(action)
        run.log.append(f"> {json.dumps(action)}\n{observation}")
    else:
        run.problems.append(f"stopped at the step limit ({max_steps}) without finishing")
    picked, seen, invented = [], set(), False
    for ref in chosen:
        pid = _passage_id(ref)
        if pid is None or pid not in run.shown:
            invented = True
            run.problems.append(f"model chose {ref!r}, which it was never shown")
        elif pid not in seen:
            seen.add(pid)
            picked.append(pid)
    passages = []
    for pid in picked:
        item_id, text = run.shown[pid]
        url, source = db.execute("SELECT url, source_id FROM item WHERE id = ?", (item_id,)).fetchone()
        fetched_at = db.execute("SELECT fetched_at FROM passage WHERE id = ?", (pid,)).fetchone()[0]
        passages.append({"id": pid, "item_id": item_id, "url": url, "source": source,
                         "text": text, "fetched_at": fetched_at})
    main_read = any(p["item_id"] == issue["item_id"] for p in passages)
    if not main_read:
        run.problems.append("no passage from the main item is in the pack")
    return {"issue": issue, "passages": passages, "gaps": gaps, "problems": run.problems,
            "steps": len(run.log) - 1 + (1 if finished else 0),
            "complete": finished and main_read and not invented}


def select_issues(db, count, copyable):
    """The best kept items with no pack yet: highest relevance first, one per topic, newest first.

    Items from link-only sources are skipped: no passage can be kept, so no editorial can quote them.
    """
    rows = db.execute(
        "SELECT i.id, i.source_id, i.title, t.topic, t.relevance FROM triage t JOIN item i ON i.id = t.item_id"
        " WHERE t.relevance >= ? AND i.id NOT IN (SELECT item_id FROM evidence_pack)"
        " ORDER BY t.relevance DESC, i.published_at DESC, i.id DESC", (KEEP_AT,)).fetchall()
    issues, topics = [], set()
    for item_id, source_id, title, topic, relevance in rows:
        if topic in topics or len(issues) >= count or not copyable.get(source_id, False):
            continue
        topics.add(topic)
        issues.append({"item_id": item_id, "source_id": source_id, "title": title, "topic": topic,
                       "relevance": relevance, "past_questions": len(past_questions(topic))})
    return issues


def run_stage(router, store, copyable, count=3, fetcher=documents.fetch, out=sys.stdout):
    store.db.executescript(SCHEMA)
    documents.ensure_schema(store.db)
    issues = select_issues(store.db, count, copyable)
    complete = failed = 0
    for issue in issues:
        try:
            pack = research(router, store.db, issue, copyable, fetcher)
        except AllRoutesFailed as error:
            failed += 1
            print(f"item {issue['item_id']}: FAILED: {error}", file=out)
            continue
        with store.db:
            store.db.execute("INSERT OR REPLACE INTO evidence_pack VALUES (?, ?, ?, ?)",
                             (issue["item_id"], json.dumps(pack), int(pack["complete"]), now()))
        complete += pack["complete"]
        state = "complete" if pack["complete"] else "INCOMPLETE: " + "; ".join(pack["problems"])
        print(f"item {issue['item_id']}: {len(pack['passages'])} passages, {state}", file=out)
    print(f"{complete}/{len(issues)} packs complete", file=out)
    if not issues:
        return 0
    return 2 if complete == 0 and failed == len(issues) else (0 if complete == len(issues) else 1)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", default="data/raw/scout.sqlite")
    parser.add_argument("--issues", type=int, default=3)
    parser.add_argument("--config", default="config/feeds.json")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    copyable = {s["id"]: bool(s.get("copy")) for s in json.load(open(args.config))}
    return run_stage(build_router(), Store(args.db), copyable, args.issues)


if __name__ == "__main__":
    sys.exit(main())
