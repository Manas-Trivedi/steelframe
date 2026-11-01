"""Backfill: research, write, check and publish issues for past days, so the site does not start empty.

    python3 -m steelframe.pipeline.backfill [--count 40] [--max-minutes 80] [--db data/raw/scout.sqlite]

A one-off, run by hand until the days are filled: for each release day in the last `backfill_days` days (config/gate.json)
it writes up to `backfill_per_day` issues, the best kept items first, one per topic per day. It takes only archive
items (older than the fresh window, see lanes.py), so the daily run keeps its own slots. It has no daily or monthly
cap: a run is bounded by --count, by --max-minutes, and by the free model quota (it stops, not rushes, when that is
used up). It does not fetch or triage: run the archive ingest and Triage first. Same kill switch, audit alarm and
exit codes as the daily run.
"""
import argparse
import json
import logging
import sys
import time

from ..scout.store import Store
from ..taxonomy import load_topics
from . import daily, gate, researcher
from .common import build_router


def run(router, store, sources, topics, config, count, max_minutes=80, out=sys.stdout):
    code = daily.stopped(store, config, out)
    if code is not None:
        return code
    deadline = time.monotonic() + max_minutes * 60
    copyable = {s["id"]: bool(s.get("copy")) for s in sources}
    queued = len(daily.waiting_packs(store.db, lane="archive"))
    researched = researcher.run_stage(router, store, copyable, max(count - queued, 0), out=out, lane="archive",
                                      per_day=config["backfill_per_day"], days=config["backfill_days"])
    published, held, failed, deferred = daily.run_issues(router, store, topics, copyable, config, out,
                                                         lane="archive", limit=count, deadline=deadline)
    print(f"archive: published {published}, held {held}, failed {failed}, deferred {deferred}; "
          f"model calls this run: {router.calls}", file=out)
    if published == 0 and (failed or held or researched == 2):
        return 2
    return 1 if (held or failed or deferred or researched) else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--count", type=int, default=40, help="most issues to decide in this run")
    parser.add_argument("--max-minutes", type=int, default=80, help="start no new issue after this long")
    parser.add_argument("--db", default="data/raw/scout.sqlite")
    parser.add_argument("--feeds", default="config/feeds.json")
    parser.add_argument("--gate", default=gate.CONFIG)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    with open(args.feeds) as f:
        sources = json.load(f)
    return run(build_router(), Store(args.db), sources, load_topics(), gate.load_config(args.gate), args.count,
               args.max_minutes)


if __name__ == "__main__":
    sys.exit(main())
