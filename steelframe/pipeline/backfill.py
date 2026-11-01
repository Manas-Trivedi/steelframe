"""Backfill: research, write, check and publish issues from the archive, the best kept items first.

    python3 -m steelframe.pipeline.backfill [--count 10] [--db data/raw/scout.sqlite] [--feeds config/feeds.json]

Takes only items older than the fresh window (see lanes.py), within the archive lane's own daily cap and the
monthly cap, so it never takes the day's news slot. It does not fetch or triage: run Triage first. Same exit
codes as the daily run, and the same kill switch and audit alarm.
"""
import argparse
import json
import logging
import sys

from ..scout.store import Store
from ..taxonomy import load_topics
from . import daily, gate, researcher
from .common import build_router


def run(router, store, sources, topics, config, count, out=sys.stdout):
    code = daily.stopped(store, config, out)
    if code is not None:
        return code
    copyable = {s["id"]: bool(s.get("copy")) for s in sources}
    room = min(count, daily.lane_room(store.db, config, "archive"))
    if room <= 0:
        print("nothing to do: the archive lane has used its cap for today or the monthly cap is reached", file=out)
        return 0
    queued = len(daily.waiting_packs(store.db, lane="archive"))
    researched = researcher.run_stage(router, store, copyable, max(room - queued, 0), out=out, lane="archive")
    published, held, failed, deferred = daily.run_issues(router, store, topics, copyable, config, out,
                                                         lane="archive", limit=room)
    print(f"archive: published {published}, held {held}, failed {failed}, deferred {deferred}; "
          f"model calls this run: {router.calls}", file=out)
    if published == 0 and (failed or held or researched == 2):
        return 2
    return 1 if (held or failed or deferred or researched) else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--count", type=int, default=10, help="most issues to decide in this run")
    parser.add_argument("--db", default="data/raw/scout.sqlite")
    parser.add_argument("--feeds", default="config/feeds.json")
    parser.add_argument("--gate", default=gate.CONFIG)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    with open(args.feeds) as f:
        sources = json.load(f)
    return run(build_router(), Store(args.db), sources, load_topics(), gate.load_config(args.gate), args.count)


if __name__ == "__main__":
    sys.exit(main())
