"""Daily audit of published pieces, and the error-rate alarm that pauses publishing.

    python3 -m steelframe.ops.audit run [--db data/raw/scout.sqlite] [--sample 3]
    python3 -m steelframe.ops.audit resume

Each day a random sample of published pieces is checked again: the code checks against the stored passages, then a
model from a provider that neither wrote the piece nor fact-checked it, when one is available. This is an automated
audit, not a human one (docs/evals/ACCURACY_AUDIT.md asks for people); it exists to catch drift between runs.

Alarm: publishing pauses when, in the last 14 days of audits, any claim is contradicted (a major error), or more than
5% of claims are not fully supported (the line the audit document draws between Accuracy 3 and 2). While paused,
the daily run publishes nothing. `resume` clears it after a person has looked.

Exit code: 0 clean, 1 an error was found or the alarm is on, 2 the audit could not run.
"""
import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone

from ..llm.errors import AllRoutesFailed
from ..pipeline import checks, fact_checker
from ..pipeline.common import build_router
from ..scout.store import Store, now
from . import corrections

WINDOW_DAYS = 14
MAX_UNSUPPORTED_RATE = 0.05

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES item (id),
    audited_at TEXT NOT NULL,
    claims INTEGER NOT NULL,
    unsupported INTEGER NOT NULL,
    contradicted INTEGER NOT NULL,
    failures TEXT NOT NULL,
    auditor TEXT
);
"""


def ensure_schema(db):
    corrections.ensure_schema(db)
    db.executescript(SCHEMA)


def published_pieces(db):
    rows = db.execute(
        "SELECT e.item_id, d.draft, d.model, p.pack, r.checker FROM editorial e"
        " JOIN draft d ON d.item_id = e.item_id AND d.attempt = e.draft_attempt"
        " JOIN evidence_pack p ON p.item_id = e.item_id"
        " LEFT JOIN review r ON r.item_id = e.item_id AND r.attempt = e.draft_attempt"
        " WHERE e.status = 'published'").fetchall()
    return [(i, json.loads(d), m, json.loads(p), c) for i, d, m, p, c in rows]


def audit_piece(router, draft, writer_model, pack, copyable, original_checker):
    """Return (claims, unsupported, contradicted, failures, auditor)."""
    claims = len(draft["claims"])
    code = checks.run_code_checks(draft, pack, copyable)
    if code:
        return claims, len(code), 0, code, None
    skip = tuple({writer_model.split("/")[0]} | ({original_checker.split("/")[0]} if original_checker else set()))
    try:
        verdicts, result = router.complete_json(
            "fact_checker", fact_checker.SYSTEM, fact_checker.build_prompt(draft, pack),
            fact_checker.make_validator([c["id"] for c in draft["claims"]], len(draft["recall_questions"])), 6000, exclude=skip)
    except AllRoutesFailed:
        # Every provider that did not write or check it is unavailable. Fall back to any provider but the writer.
        verdicts, result = router.complete_json(
            "fact_checker", fact_checker.SYSTEM, fact_checker.build_prompt(draft, pack),
            fact_checker.make_validator([c["id"] for c in draft["claims"]], len(draft["recall_questions"])), 6000,
            exclude=(writer_model.split("/")[0],))
    bad = [r for r in verdicts["claims"] if r["verdict"] != "supported"]
    major = [r for r in bad if r["verdict"] == "contradicted"]
    failures = [f"claim {r['id']} is {r['verdict']}: {r.get('note', '')}" for r in bad]
    return claims, len(bad), len(major), failures, f"{result.provider}/{result.model}"


def window_stats(db, today):
    since = (today - timedelta(days=WINDOW_DAYS)).isoformat()
    claims, unsupported, contradicted = db.execute(
        "SELECT COALESCE(SUM(claims), 0), COALESCE(SUM(unsupported), 0), COALESCE(SUM(contradicted), 0)"
        " FROM audit WHERE audited_at >= ?", (since,)).fetchone()
    return claims, unsupported, contradicted


def alarm_reason(claims, unsupported, contradicted):
    if contradicted:
        return f"{contradicted} contradicted claim(s) in the last {WINDOW_DAYS} days of audits"
    if claims and unsupported / claims > MAX_UNSUPPORTED_RATE:
        return f"{unsupported} of {claims} audited claims not fully supported (limit {MAX_UNSUPPORTED_RATE:.0%})"
    return None


def run_audit(router, db, copyable, sample=3, rng=random, today=None, out=sys.stdout):
    ensure_schema(db)
    today = today or datetime.now(timezone.utc).date()
    pieces = published_pieces(db)
    if not pieces:
        print("nothing published yet, nothing to audit", file=out)
        return 0
    errors = 0
    for item_id, draft, model, pack, checker in rng.sample(pieces, min(sample, len(pieces))):
        try:
            claims, bad, major, failures, auditor = audit_piece(router, draft, model, pack, copyable, checker)
        except AllRoutesFailed as error:
            print(f"item {item_id}: audit could not run: {error}", file=out)
            return 2
        with db:
            db.execute("INSERT INTO audit (item_id, audited_at, claims, unsupported, contradicted, failures, auditor)"
                       " VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (item_id, today.isoformat() + "T00:00:00", claims, bad, major, json.dumps(failures), auditor))
        errors += bool(bad)
        status = "clean" if not bad else f"{bad} of {claims} claims not fully supported"
        print(f"item {item_id}: {status}", file=out)
        for failure in failures:
            print(f"    ALERT {failure[:160]}", file=out)
    reason = alarm_reason(*window_stats(db, today))
    if reason:
        corrections.start_pause(db, reason)
        print(f"ALARM: publishing paused: {reason}. Fix or correct the piece, then run: python3 -m steelframe.ops.audit resume", file=out)
    return 1 if (errors or reason) else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cmd", choices=["run", "resume"])
    parser.add_argument("--db", default="data/raw/scout.sqlite")
    parser.add_argument("--sample", type=int, default=3)
    args = parser.parse_args(argv)
    db = Store(args.db).db
    if args.cmd == "resume":
        corrections.clear_pause(db)
        print("publishing resumed")
        return 0
    return run_audit(build_router(), db, {"PIB": True}, args.sample)


if __name__ == "__main__":
    sys.exit(main())
