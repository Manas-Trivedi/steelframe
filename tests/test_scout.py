import io
import socket
import unittest
import urllib.error

from steelframe.scout.feed import FeedError, parse_feed
from steelframe.scout.fetch import FetchFailed, FetchRejected, fetch
from steelframe.scout.run import run
from steelframe.scout.store import Store
from steelframe.scout.urls import canonical_url

RSS = b"""\xef\xbb\xbf<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>One</title><link>http://Example.com/a/?utm_source=x#frag</link>
<pubDate>Fri, 30 Oct 2026 18:40:00 GMT</pubDate></item>
<item><title>Two</title><link>https://example.com/b</link><pubDate>not a date</pubDate></item>
<item><title>No link</title></item>
<item><link>https://example.com/c</link></item>
</channel></rss>"""

ATOM = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>A</title>
<link href="https://example.com/x"/><updated>2026-10-30T10:00:00Z</updated></entry></feed>"""


def http_error(code):
    return urllib.error.HTTPError("u", code, "msg", {}, None)


class Opener:
    """Replays a list of results: bytes are returned, exceptions are raised."""

    def __init__(self, *results):
        self.results, self.calls = list(results), 0

    def __call__(self, request, timeout):
        self.calls += 1
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return io.BytesIO(result)


class FeedTests(unittest.TestCase):
    def test_rss_with_bom_bad_date_and_missing_fields(self):
        items, skipped = parse_feed(RSS)
        self.assertEqual([i.title for i in items], ["One", "Two"])
        self.assertEqual(skipped, 2)
        self.assertEqual(items[0].published_at, "2026-10-30T18:40:00+00:00")
        self.assertIsNone(items[1].published_at)

    def test_atom(self):
        items, _ = parse_feed(ATOM)
        self.assertEqual(items[0].published_at, "2026-10-30T10:00:00+00:00")

    def test_broken_inputs_raise_feed_error(self):
        for body in (b"", b"<rss><channel>", b"<html><body>Access denied</body></html>", b"\x00\xff"):
            with self.assertRaises(FeedError, msg=body):
                parse_feed(body)


class FetchTests(unittest.TestCase):
    def test_403_is_not_retried(self):
        opener = Opener(http_error(403))
        with self.assertRaises(FetchRejected):
            fetch("https://x.test/", opener=opener, sleep=lambda s: None)
        self.assertEqual(opener.calls, 1)

    def test_429_and_5xx_and_timeouts_are_retried_then_fail(self):
        for error in (http_error(429), http_error(503), socket.timeout("slow"), urllib.error.URLError("dns")):
            opener = Opener(error, error, error)
            with self.assertRaises(FetchFailed):
                fetch("https://x.test/", opener=opener, sleep=lambda s: None)
            self.assertEqual(opener.calls, 3)

    def test_recovers_after_one_failure(self):
        self.assertEqual(fetch("https://x.test/", opener=Opener(http_error(502), b"ok"), sleep=lambda s: None), b"ok")


class UrlTests(unittest.TestCase):
    def test_same_page_same_url(self):
        a = canonical_url("http://Example.com/a/?utm_source=x&id=2#top")
        b = canonical_url("https://example.com/a?id=2")
        self.assertEqual(a, b)


class StoreTests(unittest.TestCase):
    def test_a_later_source_dates_an_item_stored_without_a_date_and_never_changes_a_date(self):
        from steelframe.scout.feed import FeedItem
        store = Store(":memory:")
        store.add_items("PIB", [FeedItem("t", "https://x.test/a", None), FeedItem("u", "https://x.test/b", "2026-10-01")])
        self.assertEqual(store.add_items("PIB", [FeedItem("t", "https://x.test/a", "2026-10-05"),
                                                 FeedItem("u", "https://x.test/b", "2026-10-09")]), 0)
        self.assertEqual(store.db.execute("SELECT url, published_at FROM item ORDER BY url").fetchall(),
                         [("https://x.test/a", "2026-10-05"), ("https://x.test/b", "2026-10-01")])


class RunTests(unittest.TestCase):
    sources = [{"id": "A", "url": "a"}, {"id": "B", "url": "b"}]

    def go(self, responses):
        store = Store(":memory:")
        out = io.StringIO()
        code = run(self.sources, store, fetcher=lambda url: responses[url](), out=out)
        return code, store, out.getvalue()

    def test_second_run_adds_nothing(self):
        responses = {"a": lambda: RSS, "b": lambda: ATOM}
        store = Store(":memory:")
        run(self.sources, store, fetcher=lambda u: responses[u](), out=io.StringIO())
        run(self.sources, store, fetcher=lambda u: responses[u](), out=io.StringIO())
        self.assertEqual(store.db.execute("select count(*) from item").fetchone()[0], 3)

    def test_one_failing_source_does_not_hide_the_other(self):
        def boom():
            raise FetchRejected("403")
        code, store, out = self.go({"a": boom, "b": lambda: ATOM})
        self.assertEqual(code, 1)
        self.assertEqual(store.db.execute("select count(*) from item").fetchone()[0], 1)
        self.assertIn("FAILED", out)

    def test_unexpected_error_in_one_source_is_contained(self):
        def bug():
            raise KeyError("x")
        code, store, _ = self.go({"a": bug, "b": lambda: ATOM})
        self.assertEqual(code, 1)
        statuses = dict(store.db.execute("select source_id, status from source_run").fetchall())
        self.assertEqual(statuses, {"A": "failed", "B": "ok"})

    def test_everything_failing_or_empty_exits_2(self):
        def boom():
            raise FetchFailed("down")
        self.assertEqual(self.go({"a": boom, "b": boom})[0], 2)
        empty = lambda: b"<rss><channel></channel></rss>"
        code, store, _ = self.go({"a": empty, "b": empty})
        self.assertEqual(code, 2)
        self.assertEqual(store.db.execute("select count(*) from source_run where status='failed'").fetchone()[0], 2)


if __name__ == "__main__":
    unittest.main()
