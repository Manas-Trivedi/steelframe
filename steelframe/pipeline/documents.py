"""Read a stored item's full text and keep it as passages, only where the source's terms allow a copy.

PIB allows reproduction with credit. RBI forbids caching, so RBI items are never stored as passages
(docs/sources/SOURCES.md). Search runs over item titles and stored passages with SQLite full-text search.
"""
import html
import re
from html.parser import HTMLParser

from ..scout.fetch import FetchFailed, FetchRejected, fetch
from ..scout.store import now

PASSAGE_CHARS = 1500

SCHEMA = """
CREATE TABLE IF NOT EXISTS passage (
    id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES item (id),
    ordinal INTEGER NOT NULL,
    text TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    UNIQUE (item_id, ordinal)
);
CREATE VIRTUAL TABLE IF NOT EXISTS passage_fts USING fts5 (text);
CREATE VIRTUAL TABLE IF NOT EXISTS item_fts USING fts5 (title);
"""


class NotCopyable(Exception):
    """The source's terms do not allow keeping a copy of its text."""


class NoText(Exception):
    """The page was fetched but held no readable release text."""


class _Paragraphs(HTMLParser):
    """Collect the text of <p>, <li> and table rows between the date line and the release footer."""

    BLOCKS = {"p", "li", "tr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active, self.depth, self.parts, self.out = False, 0, [], []

    def handle_starttag(self, tag, attrs):
        ids = dict(attrs).get("id")
        if ids == "PrDateTime":
            self.active = True
        elif ids == "RelLink":
            self.active = False
        if self.active and tag in self.BLOCKS:
            self.depth += 1

    def handle_endtag(self, tag):
        if self.active and tag in self.BLOCKS and self.depth:
            self.depth -= 1
            if self.depth == 0:
                text = re.sub(r"\s+", " ", " ".join(self.parts)).strip()
                if text:
                    self.out.append(text)
                self.parts = []

    def handle_data(self, data):
        if self.active and self.depth:
            self.parts.append(data)


def extract_paragraphs(page):
    """Return the release's paragraphs from a PIB press-release page (bytes or str)."""
    text = page.decode("utf-8", "replace") if isinstance(page, bytes) else page
    parser = _Paragraphs()
    parser.feed(text)
    parser.close()
    return [html.unescape(p) for p in parser.out]


def chunk(paragraphs, limit=PASSAGE_CHARS):
    """Group paragraphs into passages of up to `limit` characters. A longer paragraph is split at sentences."""
    passages, current = [], ""
    pieces = []
    for paragraph in paragraphs:
        if len(paragraph) <= limit:
            pieces.append(paragraph)
            continue
        pieces += [s for s in re.split(r"(?<=[.;])\s+", paragraph)]
    for piece in pieces:
        while len(piece) > limit:  # a single sentence longer than the limit
            if current:
                passages.append(current)
                current = ""
            passages.append(piece[:limit])
            piece = piece[limit:]
        if current and len(current) + 1 + len(piece) > limit:
            passages.append(current)
            current = ""
        current = f"{current} {piece}".strip()
    if current:
        passages.append(current)
    return passages


def ensure_schema(db):
    db.executescript(SCHEMA)


def load_passages(db, item_id, copyable, fetcher=fetch):
    """Fetch an item's page and store its passages (once). Returns [(passage_id, text)].

    Raises NotCopyable, NoText, FetchRejected or FetchFailed. A second call reads from the database.
    """
    ensure_schema(db)
    row = db.execute("SELECT source_id, url FROM item WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        raise KeyError(f"no item {item_id}")
    source_id, url = row
    if not copyable.get(source_id, False):
        raise NotCopyable(f"{source_id} terms do not allow keeping a copy; link only")
    stored = db.execute("SELECT id, text FROM passage WHERE item_id = ? ORDER BY ordinal", (item_id,)).fetchall()
    if stored:
        return stored
    paragraphs = extract_paragraphs(fetcher(url))
    if not paragraphs:
        raise NoText(f"{url}: no release text found")
    stamp = now()
    with db:
        for ordinal, text in enumerate(chunk(paragraphs)):
            cursor = db.execute("INSERT INTO passage (item_id, ordinal, text, fetched_at) VALUES (?, ?, ?, ?)",
                                (item_id, ordinal, text, stamp))
            db.execute("INSERT INTO passage_fts (rowid, text) VALUES (?, ?)", (cursor.lastrowid, text))
    return db.execute("SELECT id, text FROM passage WHERE item_id = ? ORDER BY ordinal", (item_id,)).fetchall()


def _match(query):
    words = re.findall(r"\w+", query)[:12]
    return " OR ".join(f'"{w}"' for w in words)


def search(db, query, limit=8):
    """Return {"items": [(id, source_id, title)], "passages": [(passage_id, item_id, snippet)]}."""
    ensure_schema(db)
    match = _match(query)
    if not match:
        return {"items": [], "passages": []}
    db.execute("INSERT INTO item_fts (rowid, title) SELECT id, title FROM item"
               " WHERE id NOT IN (SELECT rowid FROM item_fts)")
    items = db.execute(
        "SELECT i.id, i.source_id, i.title FROM item_fts f JOIN item i ON i.id = f.rowid"
        " WHERE item_fts MATCH ? ORDER BY rank LIMIT ?", (match, limit)).fetchall()
    passages = db.execute(
        "SELECT p.id, p.item_id, snippet(passage_fts, 0, '[', ']', ' ... ', 24) FROM passage_fts f"
        " JOIN passage p ON p.id = f.rowid WHERE passage_fts MATCH ? ORDER BY rank LIMIT ?",
        (match, limit)).fetchall()
    return {"items": items, "passages": passages}
