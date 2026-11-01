"""The daily run: Scout, Triage, Researcher, then write, check, score and gate each issue.

    python3 -m steelframe.pipeline.daily [--db data/raw/scout.sqlite] [--feeds config/feeds.json] [--gate config/gate.json]

Every stage saves its result before the next starts, so a rerun resumes where the last run stopped: an issue that
was mid-revision continues from its last saved attempt. At most `daily_issue_cap` issues are decided a day; an
issue is never rushed through with fewer checks when the free quota is short, it waits for the next day.
An issue for which every model answers but none gives a usable draft, three runs in a row, is held (never for
outages, quota or auth failures, which keep retrying). `ops.corrections requeue` brings a held issue back.

Exit code: 0 everything finished and nothing was held, 1 something was held, failed or deferred (an alert), 2 nothing
was published and something failed. The kill switch (config/gate.json) stops the run before any work.
"""
import argparse
import json
import logging
import sys

from ..llm.errors import AllRoutesFailed
from ..ops import corrections as ops_corrections
from ..scout import run as scout_run
from ..scout.store import Store, now
from ..taxonomy import load_topics
from . import fact_checker, gate, lanes, researcher, triage, writer
from .common import build_router
from .examiner import examine

log = logging.getLogger("steelframe.daily")

SCHEMA = """
CREATE TABLE IF NOT EXISTS review (
    item_id INTEGER NOT NULL REFERENCES item (id),
    attempt INTEGER NOT NULL,
    failures TEXT NOT NULL,
    checker TEXT,
    exam TEXT,
    decision TEXT NOT NULL CHECK (decision IN ('publish', 'revise', 'hold')),
    reasons TEXT NOT NULL,
    calls INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (item_id, attempt)
);
CREATE TABLE IF NOT EXISTS editorial (
    item_id INTEGER PRIMARY KEY REFERENCES item (id),
    status TEXT NOT NULL CHECK (status IN ('published', 'held')),
    draft_attempt INTEGER NOT NULL,
    title TEXT NOT NULL,
    topic TEXT NOT NULL,
    reasons TEXT NOT NULL,
    decided_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stall (
    item_id INTEGER PRIMARY KEY REFERENCES item (id),
    runs INTEGER NOT NULL,
    last_reasons TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

MAX_STALLED_RUNS = 3  # runs in a row where every model answered but none gave a usable draft, then the issue is held


def ensure_schema(db):
    db.executescript(writer.SCHEMA + researcher.SCHEMA + SCHEMA)


def lane_room(db, config, lane):
    """How many more issues the lane may decide today: its own daily cap, and what is left of the monthly cap."""
    cap = config["daily_issue_cap" if lane == "fresh" else "backfill_issue_cap"]
    return max(min(cap - lanes.decided_on_day(db, lane), config["monthly_issue_cap"] - lanes.decided_in_month(db)), 0)


def waiting_packs(db, limit=None, lane=None):
    """Complete evidence packs with no decision yet, oldest first."""
    lane_sql, lane_params = lanes.clause(lane)
    rows = db.execute("SELECT p.item_id, p.pack FROM evidence_pack p JOIN item i ON i.id = p.item_id"
                      " WHERE p.complete = 1 AND p.item_id NOT IN (SELECT item_id FROM editorial) AND " + lane_sql +
                      " ORDER BY p.created_at, p.item_id", lane_params).fetchall()
    return [(item_id, json.loads(pack)) for item_id, pack in rows][:limit]


def has_headroom(router):
    """True if every model stage has at least one model with free quota left today."""
    return all(any(router.quota.allowed(f"{provider}/{model}") for provider, model in router.routes.get(stage, []))
               for stage in ("writer", "fact_checker", "examiner"))


def _unusable_answers_only(error):
    """True if every route answered (or broke) with a draft we could not use: no rate limit, auth, skip or 4xx.

    Quota, auth and outage failures must keep retrying; only a draft no model can get right is a stuck issue.
    """
    return all("unusable answer or outage" in reason for reason in error.reasons)


def _stalled(db, item_id, pack, error, out):
    """Count a run in which no model produced a usable draft; hold the issue once it has done so too often.

    Returns "held" or None. An issue that keeps failing would otherwise be retried every day at the front of the queue.
    """
    if not _unusable_answers_only(error):
        return None
    row = db.execute("SELECT runs FROM stall WHERE item_id = ?", (item_id,)).fetchone()
    runs = (row[0] if row else 0) + 1
    with db:
        db.execute("INSERT OR REPLACE INTO stall VALUES (?, ?, ?, ?)", (item_id, runs, json.dumps(error.reasons), now()))
    if runs < MAX_STALLED_RUNS:
        return None
    reasons = [f"no model produced a usable draft in {runs} runs in a row"] + error.reasons
    last = db.execute("SELECT MAX(attempt) FROM review WHERE item_id = ?", (item_id,)).fetchone()[0] or 1
    _save_editorial(db, item_id, "held", last, pack["issue"], reasons)
    print(f"item {item_id}: HELD, {reasons[0]}", file=out)
    for reason in reasons[1:]:
        print(f"    ALERT held: {reason[:160]}", file=out)
    return "held"


def _save_review(db, item_id, attempt, failures, checker, exam, decision, calls):
    with db:
        db.execute("INSERT OR REPLACE INTO review VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (item_id, attempt, json.dumps(failures), checker, json.dumps(exam) if exam else None,
                    decision.action, json.dumps(decision.reasons), calls, now()))


def _save_editorial(db, item_id, status, attempt, draft, reasons):
    with db:
        db.execute("INSERT OR REPLACE INTO editorial VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (item_id, status, attempt, draft["title"], draft["topic"], json.dumps(reasons), now()))


def process_issue(router, db, item_id, pack, topics, copyable, config, out=sys.stdout):
    """Write, check, score and gate one issue until it is published or held. Returns "published" or "held".

    Raises AllRoutesFailed if a model stage is unreachable; everything saved so far lets the next run resume.
    """
    issue = pack["issue"]
    if issue["topic"] in config["sensitive_topics"] or config["kill_switch"]:
        decision = gate.decide(1, issue["topic"], [], None, config)
        draft = {"title": issue["title"], "topic": issue["topic"]}
        _save_review(db, item_id, 1, [], None, None, decision, 0)
        _save_editorial(db, item_id, "held", 1, draft, decision.reasons)
        print(f"item {item_id}: HELD before writing: {decision.reasons[0]}", file=out)
        return "held"
    last = db.execute("SELECT attempt, decision, reasons FROM review WHERE item_id = ? ORDER BY attempt DESC LIMIT 1",
                      (item_id,)).fetchone()
    attempt, failures = (last[0] + 1, json.loads(last[2])) if last else (1, None)
    while True:
        calls_before = router.calls
        row = db.execute("SELECT draft, model FROM draft WHERE item_id = ? AND attempt = ?", (item_id, attempt)).fetchone()
        if row:  # a crash left a draft without a review: check it rather than pay for another
            draft, model = json.loads(row[0]), row[1]
        else:
            print(f"item {item_id}: attempt {attempt}: writing (a free model can take a minute or two)...", file=out, flush=True)
            draft, model = writer.write(router, pack, topics, failures)
            writer.save_draft(db, item_id, attempt, draft, model)
        writer_provider = model.split("/")[0]
        print(f"item {item_id}: attempt {attempt}: checking...", file=out, flush=True)
        fact = fact_checker.check_draft(router, draft, pack, copyable, writer_provider)
        if fact["passed"]:
            print(f"item {item_id}: attempt {attempt}: scoring...", file=out, flush=True)
        exam = examine(router, draft, fact, writer_provider, topics) if fact["passed"] else None
        decision = gate.decide(attempt, draft["topic"], fact["failures"], exam, config)
        _save_review(db, item_id, attempt, fact["failures"], fact["checker"], exam, decision, router.calls - calls_before)
        if decision.action == "revise":
            print(f"item {item_id}: attempt {attempt} failed, revising: {decision.reasons[0][:120]}", file=out)
            attempt, failures = attempt + 1, decision.reasons
            continue
        status = "published" if decision.action == "publish" else "held"
        _save_editorial(db, item_id, status, attempt, draft, decision.reasons)
        score = f", score {exam['total']}" if exam else ""
        print(f"item {item_id}: {status.upper()} after {attempt} attempt(s){score}: {draft['title'][:80]}", file=out)
        for reason in decision.reasons:
            print(f"    ALERT held: {reason[:160]}", file=out)
        return status


def run_issues(router, store, topics, copyable, config, out=sys.stdout, lane="fresh", limit=None):
    """Decide the waiting issues of a lane, up to its daily cap. Returns (published, held, failed, deferred)."""
    ensure_schema(store.db)
    room = lane_room(store.db, config, lane)
    room = room if limit is None else min(room, limit)
    published = held = failed = deferred = 0
    for item_id, pack in waiting_packs(store.db, room, lane):
        if not has_headroom(router):
            deferred += 1
            print(f"item {item_id}: deferred, free quota is used up for today", file=out)
            continue
        try:
            status = process_issue(router, store.db, item_id, pack, topics, copyable, config, out)
        except AllRoutesFailed as error:
            if _stalled(store.db, item_id, pack, error, out):
                held += 1
                continue
            failed += 1
            print(f"item {item_id}: FAILED, will resume next run: {error}", file=out)
            continue
        with store.db:
            store.db.execute("DELETE FROM stall WHERE item_id = ?", (item_id,))
        published += status == "published"
        held += status == "held"
    return published, held, failed, deferred


def stopped(store, config, out):
    """The exit code if the kill switch or the audit alarm stops the run, else None. Used by every run that writes."""
    if config["kill_switch"]:
        print("PAUSED: the kill switch is on in config/gate.json. Nothing was fetched, written or published.", file=out)
        return 0
    ensure_schema(store.db)
    paused = ops_corrections.active_pause(store.db)
    if paused:
        print(f"PAUSED by the audit alarm: {paused}. Nothing was written or published. "
              "After checking, run: python3 -m steelframe.ops.audit resume", file=out)
        return 1
    return None


def run(router, store, sources, topics, config, out=sys.stdout):
    code = stopped(store, config, out)
    if code is not None:
        return code
    copyable = {s["id"]: bool(s.get("copy")) for s in sources}
    codes = [scout_run.run(sources, store, out=out), triage.run(router, store, topics, out=out)]
    room = lane_room(store.db, config, "fresh")
    queued = len(waiting_packs(store.db, lane="fresh"))
    codes.append(researcher.run_stage(router, store, copyable, max(room - queued, 0), out=out, lane="fresh"))
    published, held, failed, deferred = run_issues(router, store, topics, copyable, config, out)
    print(f"published {published}, held {held}, failed {failed}, deferred {deferred}; model calls this run: {router.calls}",
          file=out)
    if published == 0 and (failed or held or any(c == 2 for c in codes)):
        return 2
    return 1 if (held or failed or deferred or any(codes)) else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", default="data/raw/scout.sqlite")
    parser.add_argument("--feeds", default="config/feeds.json")
    parser.add_argument("--gate", default=gate.CONFIG)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    with open(args.feeds) as f:
        sources = json.load(f)
    return run(build_router(), Store(args.db), sources, load_topics(), gate.load_config(args.gate))


if __name__ == "__main__":
    sys.exit(main())
