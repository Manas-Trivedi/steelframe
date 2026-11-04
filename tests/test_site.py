import json
import os
import shutil
import subprocess
import tempfile
import unittest

from steelframe.pipeline import daily, triage
from steelframe.scout.feed import FeedItem
from steelframe.scout.store import Store
from steelframe.site import build, render
from steelframe.taxonomy import load_topics
from tests.test_writer import good_draft, pack

SITE = {"title": "Steelframe", "tagline": "t", "base_path": ""}
TOPICS = load_topics()
HOSTILE = '<script>alert("x")</script>'


class RenderTests(unittest.TestCase):
    def test_leading_spaces_stay_outside_the_underline(self):
        out = render.render_text("First [c1] on the day [c2].")
        self.assertTrue(">on the day</span>" in out, out)

    def test_marker_wraps_the_supported_sentence_only(self):
        out = render.render_text("Intro sentence. The Centre released Rs 5 crore [c1]. Then more.")
        self.assertIn('data-claims="1"', out)
        self.assertIn(">The Centre released Rs 5 crore</span>.", out)
        self.assertNotIn("[c1]", out)
        self.assertIn("Intro sentence. <span", out)

    def test_grouped_markers_list_every_claim(self):
        self.assertIn('data-claims="3 4 5"', render.render_text("A fact [c3-c5]."))
        self.assertIn('data-claims="1 2"', render.render_text("A fact [c1, c2]."))

    def test_bullets_become_a_list_and_paragraphs_split(self):
        out = render.render_text("• One [c1].\n• Two\n\nSecond paragraph")
        self.assertIn("<ul><li>", out)
        self.assertIn("<p>Second paragraph</p>", out)

    def test_hostile_text_is_escaped_everywhere(self):
        out = render.render_text(f"{HOSTILE} [c1]. And {HOSTILE}")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_json_for_script_cannot_close_the_tag(self):
        self.assertNotIn("</script>", render.json_for_script({"a": "</script><!--"}))

    def test_mark_quote_tolerates_spacing_and_curly_quotes_and_never_marks_wrongly(self):
        marked = render.mark_quote("The ‘devolution’ was  released – on time today", "The 'devolution' was released - on time")
        self.assertIn("<mark>The ‘devolution’ was  released – on time</mark> today", marked)
        self.assertEqual(render.mark_quote("plain passage", "not there"), "plain passage")
        self.assertEqual(render.mark_quote("a <b> c", ""), "a &lt;b&gt; c")

    def test_read_minutes_rounds_up_with_a_floor_of_one(self):
        self.assertEqual(render.read_minutes("word " * 450), 3)
        self.assertEqual(render.read_minutes("short"), 1)

    def test_slugify(self):
        self.assertEqual(render.slugify("Tax devolution: Rs 1,09,019 crore!"), "tax-devolution-rs-1-09-019-crore")
        self.assertEqual(render.slugify("???"), "piece")


def seed(store, item_id, status, title="Tax devolution", topic="G2.FED", draft=None, decided="2026-11-01T06:00:00"):
    db = store.db
    store.add_items("PIB", [FeedItem(f"Title {item_id}", f"https://pib.test/{item_id}", None)])
    p = pack()
    p["issue"].update(item_id=item_id)
    draft = draft or good_draft()
    draft["title"], draft["topic"] = title, topic
    db.execute("INSERT INTO evidence_pack VALUES (?, ?, 1, 't')", (item_id, json.dumps(p)))
    db.execute("INSERT INTO draft (item_id, attempt, draft, model, created_at) VALUES (?, 1, ?, 'g/m', 't')", (item_id, json.dumps(draft)))
    db.execute("INSERT INTO triage VALUES (?, 3, ?, 'y', 'r', 'm', 't')", (item_id, topic))
    db.execute("INSERT INTO editorial VALUES (?, ?, 1, ?, ?, '[]', ?)", (item_id, status, title, topic, decided))


def make_store():
    store = Store(":memory:")
    daily.ensure_schema(store.db)
    store.db.executescript(triage.SCHEMA)
    return store


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.out)

    def build(self, store):
        return build.build(store.db, self.out, SITE, TOPICS)

    def read(self, name):
        return open(os.path.join(self.out, name), encoding="utf-8").read()

    def test_archive_piece_is_dated_by_its_source_tagged_and_keeps_a_stable_address(self):
        store = make_store()
        seed(store, 1, "published")  # undated item: shown by the day it was decided, not tagged
        seed(store, 2, "published", title="Old news")
        store.db.execute("UPDATE item SET published_at = '2026-10-14T18:30:00+00:00' WHERE id = 2")  # 15 Oct in India
        self.build(store)
        pieces = {e["item_id"]: e for e in build.load_published(store.db, TOPICS)}
        self.assertEqual((pieces[1]["date"], pieces[1]["archive"]), ("2026-11-01", False))
        self.assertEqual((pieces[2]["date"], pieces[2]["archive"]), ("2026-10-15", True))
        self.assertTrue(pieces[2]["slug"].startswith("2026-11-01-2-"))  # address uses the decision day
        self.assertEqual([e["item_id"] for e in build.load_published(store.db, TOPICS)], [1, 2])  # newest source date first
        self.assertEqual(self.read("index.html").count("From the archive"), 1)
        self.assertTrue(os.path.exists(os.path.join(self.out, "m", "2026-10.html")))

    def test_published_pieces_get_pages_and_held_ones_do_not(self):
        store = make_store()
        seed(store, 1, "published")
        seed(store, 2, "held", title="Held piece")
        result = self.build(store)
        self.assertEqual(result["editorials"], 1)
        pieces = os.listdir(os.path.join(self.out, "p"))
        self.assertEqual(len(pieces), 1)
        self.assertNotIn("Held piece", self.read("index.html"))
        for name in ("index.html", "map.html", "revision.html", "me.html", "corrections.html", "archive.html", "m/2026-11.html",
                     "assets/style.css", "assets/tokens.css", "assets/app.js", "assets/logic.js"):
            self.assertTrue(os.path.exists(os.path.join(self.out, name)), name)

    def test_piece_page_has_depths_claims_drawer_data_and_past_question_links(self):
        store = make_store()
        seed(store, 1, "published")
        self.build(store)
        page = self.read("p/" + os.listdir(os.path.join(self.out, "p"))[0])
        for needle in ('data-depth="brief"', 'data-depth="editorial"', 'data-depth="deep"', 'class="claim"', 'id="claims"',
                       "Mains question", "Recall questions", "https://www.upsc.gov.in/", 'role="dialog"',
                       '<link rel="stylesheet" href="../assets/tokens.css">'):
            self.assertTrue(needle in page, f"missing: {needle}")
        data = json.loads(page.split('id="claims">')[1].split("</script>")[0])
        self.assertIn("<mark>Rs. 1,09,019 crore</mark>", data["1"]["passage_html"])
        self.assertEqual(data["1"]["url"], "https://pib.test/1")
        self.assertNotIn("github", page.lower())

    def test_hostile_model_output_cannot_inject_markup(self):
        store = make_store()
        draft = good_draft()
        draft["title"] = HOSTILE
        draft["brief"][0] = f"{HOSTILE} [c1]."
        draft["editorial"][0]["heading"] = HOSTILE
        draft["mains_question"]["question"] = HOSTILE
        draft["recall_questions"][0]["options"][0] = HOSTILE
        draft["recall_questions"][0]["explanation"] = HOSTILE
        seed(store, 1, "published", title=HOSTILE, draft=draft)
        self.build(store)
        for name in ["index.html", "m/2026-11.html", "archive.html"] + ["p/" + n for n in os.listdir(os.path.join(self.out, "p"))]:
            text = self.read(name)
            self.assertNotIn("<script>alert", text, name)
        self.assertEqual(self.read("index.html").count("<script"), 3)  # theme snippet and the two asset tags only

    def test_map_counts_recent_pieces_by_topic(self):
        store = make_store()
        seed(store, 1, "published", decided="2026-11-01T06:00:00")
        seed(store, 2, "published", decided="2026-10-25T06:00:00", title="Another")
        seed(store, 3, "published", decided="2026-05-01T06:00:00", title="Old", topic="G3.ENV")
        from datetime import datetime, timezone
        build.build(store.db, self.out, SITE, TOPICS, links={}, today=datetime(2026, 11, 2, tzinfo=timezone.utc))
        page = self.read("map.html")
        self.assertIn("<b>2</b>", page)       # two recent pieces under G2.FED
        self.assertNotIn("Old</a>", page)     # outside 30 days
        self.assertIn("No editorials in the last 30 days.", page)

    def test_database_the_pipeline_never_ran_on_builds_an_empty_site(self):
        result = self.build(Store(":memory:"))
        self.assertEqual(result["editorials"], 0)
        self.assertTrue("Nothing has been published yet." in self.read("index.html"))

    def test_unpublishing_removes_the_old_page(self):
        store = make_store()
        seed(store, 1, "published")
        self.build(store)
        self.assertEqual(len(os.listdir(os.path.join(self.out, "p"))), 1)
        store.db.execute("UPDATE editorial SET status = 'held'")
        self.build(store)
        self.assertEqual(os.listdir(os.path.join(self.out, "p")), [])
        self.assertIn("Nothing has been published yet.", self.read("index.html"))

    def test_corrections_show_on_the_piece_and_on_the_corrections_page(self):
        store = make_store()
        seed(store, 1, "published")
        store.db.execute("CREATE TABLE correction (id INTEGER PRIMARY KEY, item_id INTEGER, noted_at TEXT, text TEXT)")
        store.db.execute("INSERT INTO correction (item_id, noted_at, text) VALUES (1, '2026-11-03T00:00:00', 'Figure fixed <b>x</b>')")
        self.build(store)
        page = self.read("p/" + os.listdir(os.path.join(self.out, "p"))[0])
        self.assertTrue("Correction, 2026-11-03" in page)
        self.assertIn("Figure fixed &lt;b&gt;x&lt;/b&gt;", self.read("corrections.html"))


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class ScriptTests(unittest.TestCase):
    def test_revision_and_streak_logic(self):
        result = subprocess.run(["node", "--test", "tests/js/logic.test.js"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout[-1500:] + result.stderr[-500:])

    def test_app_script_is_valid_javascript(self):
        for name in ("app.js", "logic.js"):
            result = subprocess.run(["node", "--check", f"site/assets/{name}"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
