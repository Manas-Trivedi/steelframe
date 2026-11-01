"""Archive ingest: fetch the last N days of PIB and RBI press releases, the ones the live feeds no longer show.

    python3 -m steelframe.scout.archive [--days 30] [--db data/raw/scout.sqlite]

PIB lists a day at a time and RBI a month at a time, both through ASP.NET forms. Items get the date of their listing
and the same URL form as the live feed, so a release is never stored twice and a rerun adds nothing.
Exit code: 0 all ok, 1 some days or months failed (the rest is still saved), 2 nothing was found.
"""
import argparse
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlencode

from .feed import IST, FeedItem
from .fetch import FetchFailed, FetchRejected, fetch
from .store import Store

PIB_LIST = "https://www.pib.gov.in/Allrel.aspx?reg=3&lang=1"  # PIB Delhi, English, all ministries
PIB_DOC = "https://pib.gov.in/PressReleaseIframePage.aspx?PRID={}"  # the link form the live feed uses
RBI_LIST = "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"
RBI_DOC = "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid={}"
PAUSE_SECONDS = 1.0  # between requests: this is a bulk read of a government site

PIB_PRID = re.compile(r"PRID=(\d+)", re.I)
RBI_ROW = re.compile(
    r"<td class=\"tableheader\"[^>]*><b>([A-Z][a-z]{2} \d{1,2}, \d{4})<b>"  # a date header, then its rows
    r"|<a class='link2' href=BS_PressReleaseDisplay\.aspx\?prid=(\d+)>(.*?)</a>", re.S)


class ArchiveError(Exception):
    """A page came back that is not the page we asked for, or not a page we can read."""


class _Page(HTMLParser):
    """Collects the form's hidden fields, the selected option of each dropdown and the PRID links."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden, self.selected, self.links = {}, {}, []
        self._select, self._link = None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "input" and a.get("type") == "hidden" and a.get("name"):
            self.hidden[a["name"]] = a.get("value") or ""
        elif tag == "select":
            self._select = a.get("name")
        elif tag == "option" and self._select and "selected" in a:
            self.selected[self._select] = a.get("value")
        elif tag == "a" and PIB_PRID.search(a.get("href") or ""):
            self._link = [PIB_PRID.search(a["href"]).group(1), ""]

    def handle_data(self, data):
        if self._link is not None:
            self._link[1] += data

    def handle_endtag(self, tag):
        if tag == "select":
            self._select = None
        elif tag == "a" and self._link is not None:
            self.links.append(tuple(self._link))
            self._link = None


def _parse(body):
    page = _Page()
    page.feed(body.decode("utf-8", "replace"))
    return page


def _midnight_ist(date):
    return datetime(date.year, date.month, date.day, tzinfo=IST).astimezone(timezone.utc).isoformat()


def pib_form(form_page, date):
    """The form values that ask PIB for one day, built from the page's own hidden fields."""
    fields = dict(form_page.hidden)
    fields.update({
        "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddlday",
        "ctl00$Bar1$ddlregion": "3", "ctl00$Bar1$ddlLang": "1", "ctl00$ContentPlaceHolder1$ddlMinistry": "0",
        "ctl00$ContentPlaceHolder1$ddlday": str(date.day),
        "ctl00$ContentPlaceHolder1$ddlMonth": str(date.month),
        "ctl00$ContentPlaceHolder1$ddlYear": str(date.year),
    })
    return urlencode(fields).encode()


def parse_pib_day(body, date):
    """Items of one PIB day. Raises ArchiveError if the page is not that day: PIB shows today's list when it
    does not understand the form, and that must not be stored under the wrong date."""
    page = _parse(body)
    got = tuple(page.selected.get(f"ctl00$ContentPlaceHolder1$ddl{k}") for k in ("day", "Month", "Year"))
    if got != (str(date.day), str(date.month), str(date.year)):
        raise ArchiveError(f"asked PIB for {date}, the page is for day/month/year {got}")
    seen, items = set(), []
    for prid, title in page.links:
        title = " ".join(unescape(title).split())
        if prid in seen or not title:
            continue
        seen.add(prid)
        items.append(FeedItem(title, PIB_DOC.format(prid), _midnight_ist(date)))
    return items


def parse_rbi_month(body, year, month):
    """Items of one RBI month, each dated by the header above it."""
    items, day = [], None
    for header, prid, title in RBI_ROW.findall(body.decode("utf-8", "replace")):
        if header:
            day = datetime.strptime(header, "%b %d, %Y")
            if (day.year, day.month) != (year, month):
                raise ArchiveError(f"asked RBI for {year}-{month:02}, the page has {header}")
        elif day is not None:
            items.append(FeedItem(" ".join(unescape(re.sub(r"<[^>]+>", "", title)).split()),
                                  RBI_DOC.format(prid), _midnight_ist(day)))
    return items


def days_back(today, days):
    return [today - timedelta(days=n) for n in range(days)]


def run(store, today, days, fetcher=fetch, sleep=time.sleep, out=sys.stdout):
    """Fetch every PIB day and RBI month in the window. Returns the exit code."""
    window = days_back(today, days)
    failures = []
    found = _run_pib(store, window, fetcher, sleep, failures, out)
    found += _run_rbi(store, window, fetcher, sleep, failures, out)
    if found == 0:
        return 2
    return 1 if failures else 0


def _run_pib(store, window, fetcher, sleep, failures, out):
    run_id = store.start_run("PIB-archive")
    found = new = 0
    try:
        form = _parse(fetcher(PIB_LIST))
    except (FetchRejected, FetchFailed) as error:
        store.finish_run(run_id, "failed", error=str(error))
        failures.append("PIB")
        print(f"PIB            FAILED: {error}", file=out)
        return 0
    for date in window:
        try:
            items = parse_pib_day(fetcher(PIB_LIST, data=pib_form(form, date)), date)
        except (FetchRejected, FetchFailed, ArchiveError) as error:
            failures.append(f"PIB {date}")
            print(f"PIB {date}  FAILED: {error}", file=out)
            continue
        found, new = found + len(items), new + store.add_items("PIB", items)
        print(f"PIB {date}  {len(items):4} items", file=out)
        sleep(PAUSE_SECONDS)
    store.finish_run(run_id, "ok", found=found, new=new, error=f"{len(failures)} days failed" if failures else None)
    print(f"PIB total       {found:4} items, {new:4} new", file=out)
    return found


def _run_rbi(store, window, fetcher, sleep, failures, out):
    run_id = store.start_run("RBI-archive")
    cutoff = _midnight_ist(window[-1])
    found = new = 0
    try:
        hidden = _parse(fetcher(RBI_LIST)).hidden
    except (FetchRejected, FetchFailed) as error:
        store.finish_run(run_id, "failed", error=str(error))
        failures.append("RBI")
        print(f"RBI            FAILED: {error}", file=out)
        return 0
    for year, month in sorted({(d.year, d.month) for d in window}):
        fields = {**hidden, "hdnYear": str(year), "hdnMonth": str(month)}
        try:
            items = [i for i in parse_rbi_month(fetcher(RBI_LIST, data=urlencode(fields).encode()), year, month)
                     if i.published_at >= cutoff]
        except (FetchRejected, FetchFailed, ArchiveError) as error:
            failures.append(f"RBI {year}-{month:02}")
            print(f"RBI {year}-{month:02}  FAILED: {error}", file=out)
            continue
        found, new = found + len(items), new + store.add_items("RBI", items)
        print(f"RBI {year}-{month:02}  {len(items):4} items", file=out)
        sleep(PAUSE_SECONDS)
    store.finish_run(run_id, "ok", found=found, new=new, error="; ".join(f for f in failures if f.startswith("RBI")) or None)
    print(f"RBI total       {found:4} items, {new:4} new", file=out)
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--db", default="data/raw/scout.sqlite")
    args = parser.parse_args(argv)
    return run(Store(args.db), datetime.now(IST).date(), args.days)


if __name__ == "__main__":
    sys.exit(main())
