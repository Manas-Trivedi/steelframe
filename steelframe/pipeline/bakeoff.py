"""Writer bake-off: run each candidate free model on the same evidence packs and compare.

    python3 -m steelframe.pipeline.bakeoff [--db data/raw/scout.sqlite] [--packs 3] [--models provider/model ...]

For each (model, pack): did the answer have the right shape, did the quote/link/figure checks pass, and what total
did an independent Examiner (never on the candidate's provider) give. The fact-check model is not run here, to save
free quota; the code checks already catch invented quotes and figures. Prints a markdown table.
"""
import argparse
import json
import sys
import time

from ..llm.errors import AllRoutesFailed
from ..scout.store import Store
from ..taxonomy import load_topics
from . import checks, examiner, writer
from .common import build_router

DEFAULT_CANDIDATES = [
    "gemini/gemini-3.5-flash", "gemini/gemini-3-flash-preview", "gemini/gemini-3.1-flash-lite",
    "groq/openai/gpt-oss-120b", "groq/qwen/qwen3.8-27b", "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
    "openrouter/google/gemma-4-31b-it:free",
]


def split(candidate):
    provider, _, model = candidate.partition("/")
    return provider, model


def try_candidate(router, candidate, pack, topics, copyable):
    """Return a dict: shape_ok, code_ok, total, seconds, note."""
    provider, model = split(candidate)
    original = router.routes["writer"]
    router.routes["writer"] = [(provider, model)]
    started = time.time()
    try:
        draft, _ = writer.write(router, pack, topics)
    except AllRoutesFailed as error:
        return {"shape_ok": False, "code_ok": False, "total": None, "seconds": time.time() - started,
                "note": str(error)[:120]}
    finally:
        router.routes["writer"] = original
    seconds = time.time() - started
    failures = checks.run_code_checks(draft, pack, copyable)
    if failures:
        return {"shape_ok": True, "code_ok": False, "total": None, "seconds": seconds, "note": failures[0][:120]}
    exam = examiner.examine(router, draft, {"checker": "code"}, provider, topics)
    return {"shape_ok": True, "code_ok": True, "total": exam["total"], "seconds": seconds, "note": ""}


def summarise(results):
    """results: {candidate: [result dicts]} -> markdown table."""
    lines = ["| Model | Packs | Valid shape | Code checks pass | Mean score | Mean seconds |", "|---|---|---|---|---|---|"]
    for candidate, rows in results.items():
        scores = [r["total"] for r in rows if r["total"] is not None]
        mean = f"{sum(scores) / len(scores):.1f}" if scores else "n/a"
        seconds = f"{sum(r['seconds'] for r in rows) / len(rows):.0f}"
        lines.append(f"| {candidate} | {len(rows)} | {sum(r['shape_ok'] for r in rows)} | "
                     f"{sum(r['code_ok'] for r in rows)} | {mean} | {seconds} |")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", default="data/raw/scout.sqlite")
    parser.add_argument("--packs", type=int, default=3)
    parser.add_argument("--models", nargs="*", default=DEFAULT_CANDIDATES)
    args = parser.parse_args(argv)
    store = Store(args.db)
    packs = [json.loads(p) for (p,) in store.db.execute(
        "SELECT pack FROM evidence_pack WHERE complete = 1 ORDER BY item_id LIMIT ?", (args.packs,))]
    if not packs:
        print("no complete evidence packs; run the Researcher first")
        return 2
    router, topics, copyable = build_router(), load_topics(), {"PIB": True}
    results = {}
    for candidate in args.models:
        results[candidate] = []
        for pack in packs:
            result = try_candidate(router, candidate, pack, topics, copyable)
            results[candidate].append(result)
            print(f"{candidate:60} item {pack['issue']['item_id']}: {result}", file=sys.stderr)
    print(summarise(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
