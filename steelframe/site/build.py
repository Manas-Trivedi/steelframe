"""Build the static site from the database.

    python3 -m steelframe.site.build [--db data/raw/scout.sqlite] [--out site/dist] [--site site/site.json]

Only editorials with status 'published' are written. A held piece never reaches the site. The output directory is
emptied of old pieces first, so a piece that is no longer published disappears.
"""
import argparse
import csv
import json
import os
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from ..pipeline import daily, lanes, triage
from ..scout.feed import IST
from ..scout.store import Store
from ..taxonomy import load_topics, past_questions
from . import pages
from .render import read_minutes, slugify, depth_texts

ASSETS = "site/assets"
PAPER_LINKS = "data/past_papers/index.csv"


def load_published(db, topics):
    """Published editorials, newest first, each with its draft, evidence pack and score."""
    names = {t["id"]: t["name"] for t in topics}
    rows = db.execute(
        "SELECT e.item_id, e.decided_at, e.draft_attempt, d.draft, p.pack, t.relevance, i.published_at"
        " FROM editorial e JOIN draft d ON d.item_id = e.item_id AND d.attempt = e.draft_attempt"
        " JOIN evidence_pack p ON p.item_id = e.item_id LEFT JOIN triage t ON t.item_id = e.item_id"
        " JOIN item i ON i.id = e.item_id WHERE e.status = 'published'").fetchall()
    corrections = load_corrections(db)
    out = []
    for item_id, decided_at, _, draft_json, pack_json, relevance, published_at in rows:
        draft = json.loads(draft_json)
        brief, editorial, deep = depth_texts(draft)
        slug_date = decided_at[:10]  # the address must not change when a piece is dated by its source
        date, archive = _source_date(published_at, decided_at)
        out.append({
            "item_id": item_id, "date": date, "archive": archive,
            "slug": f"{slug_date}-{item_id}-{slugify(draft['title'])}",
            "title": draft["title"], "topic": draft["topic"], "topic_name": names.get(draft["topic"], draft["topic"]),
            "draft": draft, "pack": json.loads(pack_json), "relevance": relevance or 2,
            "minutes": {"brief": read_minutes(brief), "editorial": read_minutes(editorial), "deep": read_minutes(deep)},
            "corrections": corrections.get(item_id, [])})
    out.sort(key=lambda e: (e["date"], e["item_id"]), reverse=True)
    return out


def _source_date(published_at, decided_at):
    """(date shown, from the archive?). A piece is dated by its source (in India), or by the day it was decided
    when the source gives no date. It is an archive piece if the source is older than the fresh window."""
    if not published_at:
        return decided_at[:10], False
    published = datetime.fromisoformat(published_at)
    decided = datetime.fromisoformat(decided_at)
    if decided.tzinfo is None:
        decided = decided.replace(tzinfo=timezone.utc)
    return (published.astimezone(IST).strftime("%Y-%m-%d"),
            published < decided - timedelta(days=lanes.FRESH_DAYS))


def load_corrections(db):
    exists = db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'correction'").fetchone()
    if not exists:
        return {}
    found = defaultdict(list)
    for item_id, noted_at, text in db.execute("SELECT item_id, noted_at, text FROM correction ORDER BY noted_at"):
        found[item_id].append({"date": noted_at[:10], "text": text})
    return found


def all_corrections(db, live_slugs):
    """Every correction, newest first, including takedowns. A taken-down piece has no page, so no link."""
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'correction'").fetchone():
        return []
    rows = db.execute("SELECT c.item_id, c.noted_at, c.text, e.title FROM correction c"
                      " LEFT JOIN editorial e ON e.item_id = c.item_id ORDER BY c.noted_at DESC").fetchall()
    return [{"date": noted[:10], "text": text, "title": title or f"Item {item_id}", "slug": live_slugs.get(item_id)}
            for item_id, noted, text, title in rows]


def paper_links(path=PAPER_LINKS):
    with open(path, encoding="utf-8") as f:
        return {(r["year"], r["stage"], r["paper"]): r["official_url"] for r in csv.DictReader(f)}


def past_links_for(topic, links, limit=8):
    """[(label, official paper url)] for questions tagged to the topic, newest year first."""
    found = sorted(past_questions(topic), reverse=True)[:limit]
    return [(f"{year} {stage} {paper}, question {n}", links.get((year, stage, paper), "#"))
            for year, stage, paper, n, _ in found]


def build(db, out_dir, site, topics, assets=ASSETS, links=None, today=None):
    daily.ensure_schema(db)  # a database the pipeline has never run on has no tables yet: build an empty site
    db.executescript(triage.SCHEMA)
    links = links if links is not None else paper_links()
    today = today or datetime.now(timezone.utc)
    editorials = load_published(db, topics)
    for sub in ("p", "m"):
        shutil.rmtree(os.path.join(out_dir, sub), ignore_errors=True)
        os.makedirs(os.path.join(out_dir, sub))
    shutil.rmtree(os.path.join(out_dir, "assets"), ignore_errors=True)
    shutil.copytree(assets, os.path.join(out_dir, "assets"))

    def write(name, text):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(text)

    write("index.html", pages.index_page(site, editorials[:20]))
    for e in editorials:
        write(f"p/{e['slug']}.html", pages.editorial_page(site, e, past_links_for(e["topic"], links)))
    months = defaultdict(list)
    for e in editorials:
        months[e["date"][:7]].append(e)
    listing = []
    for key, items in sorted(months.items(), reverse=True):
        label = datetime.strptime(key, "%Y-%m").strftime("%B %Y")
        write(f"m/{key}.html", pages.month_page(site, label, items))
        listing.append((key, label, len(items)))
    write("archive.html", pages.months_index(site, listing))
    cutoff = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    counts, recent = defaultdict(int), defaultdict(list)
    for e in editorials:
        if e["date"] >= cutoff:
            counts[e["topic"]] += 1
            recent[e["topic"]].append((e["title"], f"p/{e['slug']}.html"))
    write("map.html", pages.map_page(site, topics, counts, recent))
    write("revision.html", pages.revision_page(site))
    write("me.html", pages.me_page(site))
    write("corrections.html", pages.corrections_page(site, all_corrections(db, {e["item_id"]: e["slug"] for e in editorials})))
    return {"editorials": len(editorials), "months": len(listing)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", default="data/raw/scout.sqlite")
    parser.add_argument("--out", default="site/dist")
    parser.add_argument("--site", default="site/site.json")
    args = parser.parse_args(argv)
    with open(args.site, encoding="utf-8") as f:
        site = json.load(f)
    result = build(Store(args.db).db, args.out, site, load_topics())
    print(f"built {result['editorials']} editorials into {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
