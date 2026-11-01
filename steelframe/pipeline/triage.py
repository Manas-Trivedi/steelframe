"""Triage: score each new item's exam relevance and tag a syllabus topic. Titles only, 25 per call.

    python3 -m steelframe.pipeline.triage [--db data/raw/scout.sqlite] [--limit 200]

Exit code: 0 all batches done, 1 some batch failed (its items stay untriaged and are retried next run),
2 every batch failed. Nothing to triage is not an error: Scout is what fails loudly on an empty day.
"""
import argparse
import logging
import sys

from ..llm.errors import AllRoutesFailed
from ..scout.store import Store, now
from ..taxonomy import load_topics, past_questions
from .common import build_router

log = logging.getLogger("steelframe.triage")
BATCH = 25
KEEP_AT = 2  # relevance at or above this goes on to the Researcher

SCHEMA = """
CREATE TABLE IF NOT EXISTS triage (
    item_id INTEGER PRIMARY KEY REFERENCES item (id),
    relevance INTEGER NOT NULL CHECK (relevance BETWEEN 0 AND 3),
    topic TEXT NOT NULL,
    ca TEXT NOT NULL CHECK (ca IN ('y', 'n')),
    reason TEXT NOT NULL,
    model TEXT NOT NULL,
    triaged_at TEXT NOT NULL
);
"""

SYSTEM = """You help prepare the UPSC Civil Services Examination (India). You read press-release and \
circular titles from official Indian sources and judge how useful each is for General Studies \
current-affairs preparation.

Relevance:
0 = no exam use: ceremonies, greetings, speeches' text, routine visits, local events, awards, promotions
1 = marginal: minor event, a single scheme update with no policy content
2 = useful: a scheme, programme, report, data release, or ministry decision an answer could cite
3 = high: a law, rule, court order, treaty, committee report, major policy or economic decision

Rules:
- Judge only from the title. If it is unclear, give a lower score. Never invent details.
- topic must be one id from the topic list. Use X.OTHER when nothing fits.
- ca is "y" if answering a question on it needs recent news, "n" if it is static knowledge.
- reason is at most 12 words.

Reply with JSON only: {"items": [{"n": 1, "relevance": 0, "topic": "G2.POLICY", "ca": "y", "reason": "..."}]}
with exactly one entry per input line, using the line numbers given."""


def topic_list(topics):
    return "\n".join(f"{t['id']}: {t['name']}. {t.get('covers', '')}" for t in topics)


def make_validator(count, topic_ids):
    def validate(obj):
        rows = obj.get("items") if isinstance(obj, dict) else None
        if not isinstance(rows, list):
            raise ValueError("answer has no 'items' list")
        seen = []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("n"), int):
                raise ValueError(f"bad entry: {row!r}")
            if isinstance(row.get("relevance"), bool) or row.get("relevance") not in (0, 1, 2, 3):
                raise ValueError(f"item {row['n']}: relevance must be 0 to 3")
            if row.get("topic") not in topic_ids:
                raise ValueError(f"item {row['n']}: unknown topic {row.get('topic')!r}")
            if row.get("ca") not in ("y", "n"):
                raise ValueError(f"item {row['n']}: ca must be y or n")
            if not isinstance(row.get("reason"), str):
                raise ValueError(f"item {row['n']}: reason must be text")
            seen.append(row["n"])
        if sorted(seen) != list(range(1, count + 1)):
            raise ValueError(f"expected one entry for each of 1..{count}, got {sorted(seen)}")
    return validate


def triage_titles(router, titles, topics):
    """Return [(relevance, topic, ca, reason)] in input order, and the model used. Raises AllRoutesFailed."""
    lines = "\n".join(f"{i}. {title}" for i, title in enumerate(titles, 1))
    user = f"Topics:\n{topic_list(topics)}\n\nTitles:\n{lines}"
    parsed, result = router.complete_json(
        "triage", SYSTEM, user, make_validator(len(titles), {t["id"] for t in topics}), max_tokens=4096)
    by_n = {row["n"]: row for row in parsed["items"]}
    rows = [(by_n[i]["relevance"], by_n[i]["topic"], by_n[i]["ca"], by_n[i]["reason"].strip())
            for i in range(1, len(titles) + 1)]
    return rows, f"{result.provider}/{result.model}"


def pending_items(db, limit):
    return db.execute(
        "SELECT id, title FROM item WHERE id NOT IN (SELECT item_id FROM triage)"
        " ORDER BY COALESCE(published_at, fetched_at) DESC, id DESC LIMIT ?", (limit,)).fetchall()


def run(router, store, topics, limit=200, out=sys.stdout):
    store.db.executescript(SCHEMA)
    items = pending_items(store.db, limit)
    done = failed = 0
    batches = [items[i:i + BATCH] for i in range(0, len(items), BATCH)]
    for batch in batches:
        try:
            rows, model = triage_titles(router, [title for _, title in batch], topics)
        except AllRoutesFailed as error:
            failed += 1
            print(f"batch of {len(batch)} FAILED: {error}", file=out)
            continue
        with store.db:  # one batch is all-or-nothing
            for (item_id, _), (relevance, topic, ca, reason) in zip(batch, rows):
                store.db.execute("INSERT OR REPLACE INTO triage VALUES (?, ?, ?, ?, ?, ?, ?)",
                                 (item_id, relevance, topic, ca, reason, model, now()))
        done += len(batch)
    kept = store.db.execute("SELECT COUNT(*) FROM triage WHERE relevance >= ?", (KEEP_AT,)).fetchone()[0]
    print(f"triaged {done} items in {len(batches) - failed}/{len(batches)} batches; {kept} kept in total", file=out)
    if failed:
        return 2 if failed == len(batches) else 1
    return 0


def kept_with_links(db):
    """Kept items with their topic and how many past questions sit under the topic."""
    rows = db.execute("SELECT i.id, i.title, i.url, t.topic, t.relevance FROM triage t JOIN item i ON i.id = t.item_id"
                      " WHERE t.relevance >= ? ORDER BY t.relevance DESC, COALESCE(i.published_at, i.fetched_at) DESC", (KEEP_AT,)).fetchall()
    return [(*row, len(past_questions(row[3]))) for row in rows]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", default="data/raw/scout.sqlite")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    return run(build_router(), Store(args.db), load_topics(), args.limit)


if __name__ == "__main__":
    sys.exit(main())
