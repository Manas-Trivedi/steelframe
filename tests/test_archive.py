import io
import unittest
from datetime import date
from urllib.parse import parse_qs

from steelframe.scout import archive
from steelframe.scout.fetch import FetchFailed, FetchRejected
from steelframe.scout.store import Store

DAY = date(2026, 10, 15)


def pib_page(day, month, year, links):
    """A trimmed PIB listing: hidden form fields, the three date dropdowns, and the release links."""
    anchors = "".join(f'<a href="/PressReleaseDetail.aspx?PRID={p}">{t}</a>' for p, t in links)
    return (f'<form><input type="hidden" name="__VIEWSTATE" value="vs"/><input name="__EVENTVALIDATION" '
            f'type="hidden" value="ev"/><select name="ctl00$ContentPlaceHolder1$ddlday">'
            f'<option value="0">All</option><option selected="selected" value="{day}">{day}</option></select>'
            f'<select name="ctl00$ContentPlaceHolder1$ddlMonth"><option selected="selected" value="{month}">m</option>'
            f'</select><select name="ctl00$ContentPlaceHolder1$ddlYear"><option selected="selected" value="{year}">y'
            f'</option></select>{anchors}</form>').encode()


def rbi_rows(*days):
    return "".join(f'<tr><td class="tableheader" colspan="4" align="left"><b>{d}<b></td></tr>'
                   f"<tr><td><a class='link2' href=BS_PressReleaseDisplay.aspx?prid={p}>{t}</a></td></tr>"
                   for d, p, t in days).encode()


RBI_MONTH = rbi_rows(("Oct 30, 2026", 63897, "Premature redemption &amp; SGB"),
                     ("Oct 05, 2026", 63710, "Auction of <i>Bills</i>"))
RBI_SEPT = rbi_rows(("Sep 25, 2026", 63600, "In the window"), ("Sep 05, 2026", 63500, "Too old"))


class Site:
    """A fake fetcher: a GET returns the form page, a POST returns the listing for the day or month asked."""

    def __init__(self, pib=None, rbi=RBI_MONTH, fail_days=()):
        self.pib, self.rbi, self.fail_days, self.posts = pib, rbi, set(fail_days), []

    def __call__(self, url, data=None):
        if data is None:
            return pib_page(1, 1, 2026, []) if url == archive.PIB_LIST else b'<input type="hidden" name="hdnYear"/>' \
                b'<input type="hidden" name="__VIEWSTATE" value="rvs"/>'
        form = {k: v[0] for k, v in parse_qs(data.decode()).items()}
        self.posts.append(form)
        if url == archive.RBI_LIST:
            return self.rbi(int(form["hdnMonth"])) if callable(self.rbi) else self.rbi
        day = int(form["ctl00$ContentPlaceHolder1$ddlday"])
        if day in self.fail_days:
            raise FetchFailed("boom")
        if self.pib is not None:
            return self.pib(day, int(form["ctl00$ContentPlaceHolder1$ddlMonth"]), int(form["ctl00$ContentPlaceHolder1$ddlYear"]))
        return pib_page(day, form["ctl00$ContentPlaceHolder1$ddlMonth"], form["ctl00$ContentPlaceHolder1$ddlYear"],
                        [(1000 + day, f"Release &amp; day {day}")])


class ParseTests(unittest.TestCase):
    def test_pib_day_uses_live_feed_url_and_the_day_as_date(self):
        body = pib_page(15, 10, 2026, [(5, "A &amp; B"), (5, "A &amp; B"), (6, "  "), (7, "Two\n  lines")])
        items = archive.parse_pib_day(body, DAY)
        self.assertEqual([i.title for i in items], ["A & B", "Two lines"])  # duplicate and empty title dropped
        self.assertEqual(items[0].link, "https://pib.gov.in/PressReleaseIframePage.aspx?PRID=5")
        self.assertEqual(items[0].published_at, "2026-10-14T18:30:00+00:00")  # midnight IST

    def test_pib_showing_another_day_is_an_error_not_wrong_data(self):
        with self.assertRaises(archive.ArchiveError):
            archive.parse_pib_day(pib_page(1, 11, 2026, [(5, "x")]), DAY)

    def test_pib_broken_pages_raise_archive_error(self):
        for body in (b"", b"<html>Access denied</html>", b"\x00\xff"):
            with self.assertRaises(archive.ArchiveError, msg=body):
                archive.parse_pib_day(body, DAY)

    def test_pib_day_with_no_releases_is_empty(self):
        self.assertEqual(archive.parse_pib_day(pib_page(15, 10, 2026, []), DAY), [])

    def test_rbi_month_dates_each_row_by_its_header(self):
        items = archive.parse_rbi_month(RBI_MONTH, 2026, 10)
        self.assertEqual([(i.title, i.published_at[:10]) for i in items],
                         [("Premature redemption & SGB", "2026-10-29"), ("Auction of Bills", "2026-10-04")])
        self.assertEqual(items[0].link, "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=63897")

    def test_rbi_wrong_month_is_an_error(self):
        with self.assertRaises(archive.ArchiveError):
            archive.parse_rbi_month(RBI_SEPT, 2026, 10)


class RunTests(unittest.TestCase):
    def setUp(self):
        self.store, self.out = Store(":memory:"), io.StringIO()

    def go(self, site, days=3, today=DAY):
        return archive.run(self.store, today, days, fetcher=site, sleep=lambda s: None, out=self.out)

    def count(self, source):
        return self.store.db.execute("SELECT COUNT(*) FROM item WHERE source_id = ?", (source,)).fetchone()[0]

    def test_stores_each_day_once_and_a_rerun_adds_nothing(self):
        site = Site(rbi=b"<html></html>")
        self.assertEqual(self.go(site), 0)
        self.assertEqual(self.count("PIB"), 3)
        self.go(site)
        self.assertEqual(self.count("PIB"), 3)

    def test_same_release_as_the_live_feed_is_not_stored_twice(self):
        self.store.add_items("PIB", [archive.FeedItem("live", "https://pib.gov.in/PressReleaseIframePage.aspx?PRID=1015",
                                                      None)])
        self.go(Site(rbi=b"<html></html>"), days=1)
        self.assertEqual(self.count("PIB"), 1)

    def test_rbi_rows_before_the_window_are_left_out(self):
        site = Site(pib=lambda d, m, y: pib_page(d, m, y, []), rbi=lambda m: RBI_SEPT if m == 9 else RBI_MONTH)
        self.go(site, days=40, today=date(2026, 10, 31))  # window starts 22 Sep
        titles = [r[0] for r in self.store.db.execute("SELECT title FROM item WHERE source_id = 'RBI'")]
        self.assertEqual(sorted(titles), ["Auction of Bills", "In the window", "Premature redemption & SGB"])

    def test_one_failed_day_is_reported_and_the_rest_is_saved(self):
        self.assertEqual(self.go(Site(rbi=b"<html></html>", fail_days={14})), 1)
        self.assertEqual(self.count("PIB"), 2)
        self.assertIn("PIB 2026-10-14  FAILED", self.out.getvalue())

    def test_page_for_the_wrong_day_is_not_stored(self):
        site = Site(pib=lambda d, m, y: pib_page(1, 1, 2026, [(1, "today's list")]), rbi=b"<html></html>")
        self.assertEqual(self.go(site), 2)  # nothing found at all
        self.assertEqual(self.count("PIB"), 0)

    def test_everything_down_exits_2_and_says_why(self):
        def down(url, data=None):
            raise FetchRejected("HTTP 403")
        self.assertEqual(self.go(down), 2)
        self.assertIn("PIB            FAILED", self.out.getvalue())


if __name__ == "__main__":
    unittest.main()
