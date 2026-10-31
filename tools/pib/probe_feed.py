"""Find which PIB feed address returns English titles.

    python3 tools/pib/probe_feed.py

Tries a few Lang and Regid values, two seconds apart, and prints the first title of each reply with
its script. Uses the same plain, honest user agent as Scout.
"""
import re
import sys
import time

sys.path.insert(0, ".")
from steelframe.scout.feed import FeedError, parse_feed  # noqa: E402
from steelframe.scout.fetch import FetchFailed, FetchRejected, fetch  # noqa: E402

BASE = "https://www.pib.gov.in/RssMain.aspx?ModId=6&Lang={lang}&Regid={reg}"


def script_of(text):
    return "Hindi" if re.search(r"[ऀ-ॿ]", text) else "English" if re.search(r"[A-Za-z]", text) else "?"


def main():
    for lang in (1, 2):
        for reg in range(1, 7):
            url = BASE.format(lang=lang, reg=reg)
            try:
                items, _ = parse_feed(fetch(url, attempts=1))
                first = items[0].title if items else "(no items)"
                print(f"Lang={lang} Regid={reg}  {len(items):3} items  {script_of(first):8} {first[:60]}")
            except (FetchRejected, FetchFailed, FeedError) as error:
                print(f"Lang={lang} Regid={reg}  failed: {str(error)[:80]}")
            time.sleep(2)


if __name__ == "__main__":
    main()
