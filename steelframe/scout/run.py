"""Run Scout: fetch every configured feed and store new items.

Exit code: 0 all sources ok, 1 some sources failed, 2 every source failed or nothing was found.
A non-zero exit lets the scheduler alert, so an outage is never reported as a quiet news day.

    python3 -m steelframe.scout.run [--config config/feeds.json] [--db data/raw/scout.sqlite]
"""
import argparse
import json
import re
import sys

from .feed import FeedError, parse_feed
from .fetch import FetchFailed, FetchRejected, fetch
from .store import Store


DEVANAGARI = re.compile(r"[\u0900-\u097F]")  # the PIB English feed also carries Hindi releases; the product is English only


def scout_source(source, store, fetcher=fetch):
    """Fetch one source and store its items. Returns (status, found, new, error)."""
    run_id = store.start_run(source["id"])
    try:
        items, skipped = parse_feed(fetcher(source["url"]))
        english = [i for i in items if not DEVANAGARI.search(i.title)]
        skipped += len(items) - len(english)
        new = store.add_items(source["id"], english)
    except (FetchRejected, FetchFailed, FeedError) as error:
        store.finish_run(run_id, "failed", error=str(error))
        return "failed", 0, 0, str(error)
    except Exception as error:  # an unexpected fault in one source must not stop the others
        message = f"unexpected {type(error).__name__}: {error}"
        store.finish_run(run_id, "failed", error=message)
        return "failed", 0, 0, message
    if not items:
        # A feed that parses but is empty is suspicious, so it counts as a failure.
        error = "feed parsed but held no items"
        store.finish_run(run_id, "failed", skipped=skipped, error=error)
        return "failed", 0, 0, error
    store.finish_run(run_id, "ok", found=len(items), new=new, skipped=skipped)
    return "ok", len(items), new, None


def run(sources, store, fetcher=fetch, out=sys.stdout):
    results = []
    for source in sources:
        status, found, new, error = scout_source(source, store, fetcher)
        results.append((source["id"], status, found, new, error))
        detail = f"{found} items, {new} new" if status == "ok" else f"FAILED: {error}"
        print(f"{source['id']:14} {detail}", file=out)
    failed = [r for r in results if r[1] == "failed"]
    total_found = sum(r[2] for r in results)
    if len(failed) == len(results) or total_found == 0:
        return 2
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="config/feeds.json")
    parser.add_argument("--db", default="data/raw/scout.sqlite")
    args = parser.parse_args(argv)
    with open(args.config) as f:
        sources = json.load(f)
    return run(sources, Store(args.db))


if __name__ == "__main__":
    sys.exit(main())
