"""Find a PIB source that returns English titles.

    python3 tools/pib/probe_feed.py

Part 1 tries the RSS feed with different ModId values. Part 2 reads PIB's "all releases" page and lists the
release links it finds. Requests are two seconds apart and use Scout's plain, honest user agent.
"""
import re
import sys
import time

sys.path.insert(0, ".")
from steelframe.scout.feed import FeedError, parse_feed  # noqa: E402
from steelframe.scout.fetch import FetchFailed, FetchRejected, fetch  # noqa: E402

FEED = "https://www.pib.gov.in/RssMain.aspx?ModId={mod}&Lang=1&Regid=3"
PAGE = "https://www.pib.gov.in/allRel.aspx"


def script_of(text):
    return "Hindi" if re.search(r"[ऀ-ॿ]", text) else "English" if re.search(r"[A-Za-z]", text) else "?"


def feeds():
    print("== RSS feed, Lang=1 Regid=3, different ModId")
    for mod in range(1, 13):
        try:
            items, _ = parse_feed(fetch(FEED.format(mod=mod), attempts=1))
            first = items[0].title if items else "(no items)"
            print(f"ModId={mod:<2} {len(items):3} items  {script_of(first):8} {first[:60]}")
        except (FetchRejected, FetchFailed, FeedError) as error:
            print(f"ModId={mod:<2} failed: {str(error)[:80]}")
        time.sleep(2)


def page():
    print("== All releases page")
    try:
        html = fetch(PAGE, attempts=1).decode("utf-8", "replace")
    except (FetchRejected, FetchFailed) as error:
        print(f"failed: {error}")
        return
    links = re.findall(r'<a[^>]+href="([^"]*PRID=\d+[^"]*)"[^>]*>(.*?)</a>', html, flags=re.S | re.I)
    print(f"{len(html)} bytes, {len(links)} release links")
    for href, label in links[:8]:
        text = re.sub(r"<[^>]+>|\s+", " ", label).strip()
        print(f"  {script_of(text):8} {text[:60]}  <- {href[:60]}")


if __name__ == "__main__":
    feeds()
    page()
