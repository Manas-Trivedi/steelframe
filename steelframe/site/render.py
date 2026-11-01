"""Turn one published editorial into HTML. Every piece of text from a model or a source page is escaped here.

A claim in the text is marked [c1]. The sentence before the marker becomes a button that opens the source drawer.
"""
import html
import json
import math
import re

from ..pipeline.checks import MARKER, cited_ids, normalise

WORDS_PER_MINUTE = 200  # assumption, see docs/design/DESIGN_DIRECTION.md
SENTENCE_BREAKS = (". ", "! ", "? ", "; ")


def esc(text):
    return html.escape(str(text), quote=True)


def read_minutes(text):
    return max(1, math.ceil(len(text.split()) / WORDS_PER_MINUTE))


def slugify(text, limit=50):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:limit].strip("-")
    return slug or "piece"


def json_for_script(value):
    """JSON safe to place inside a <script type="application/json"> tag."""
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _sentence_start(segment):
    start = 0
    for token in SENTENCE_BREAKS:
        found = segment.rfind(token)
        if found != -1:
            start = max(start, found + len(token))
    newline = segment.rfind("\n")
    return max(start, newline + 1)


def render_paragraph(text):
    """Escape a paragraph and turn each [c#] marker into a button around the sentence it supports."""
    out, position = [], 0
    for match in MARKER.finditer(text):
        segment = text[position:match.start()]
        start = _sentence_start(segment)
        while start < len(segment) and segment[start].isspace():
            start += 1  # leading spaces stay outside the underline
        claim_text = segment[start:].rstrip()
        gap = segment[start:][len(claim_text):]
        if text[match.end():match.end() + 1] in (".", ",", ";", ":", "!", "?"):
            gap = ""  # keep the full stop next to the words, not after a space
        ids = " ".join(str(i) for i in sorted(cited_ids(match.group())))
        out.append(esc(segment[:start]))
        if claim_text:
            out.append(f'<span class="claim" role="button" tabindex="0" data-claims="{esc(ids)}" '
                       f'aria-label="Sourced claim. Press Enter to see the source.">{esc(claim_text)}</span>')
        out.append(esc(gap))
        position = match.end()
    out.append(esc(text[position:]))
    return "".join(out)


def render_text(text):
    """Blank lines split paragraphs; a line starting with a bullet becomes a list item."""
    blocks = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if lines and all(line[:1] in "•-*" for line in lines):
            items = "".join(f"<li>{render_paragraph(line[1:].strip())}</li>" for line in lines)
            blocks.append(f"<ul>{items}</ul>")
        else:
            blocks.append("<p>" + "<br>".join(render_paragraph(line) for line in lines) + "</p>")
    return "".join(blocks)


def _char_pattern(char):
    classes = {"'": "'‘’", "‘": "'‘’", "’": "'‘’",
               '"': '"“”', "“": '"“”', "”": '"“”',
               "-": "-–—", "–": "-–—", "—": "-–—"}
    return f"[{classes[char]}]" if char in classes else re.escape(char)


def mark_quote(passage, quote):
    """Escaped passage HTML with the quoted words in <mark>. If the quote is not found, no mark is added."""
    words = normalise(quote).split(" ")
    pattern = r"\s+".join("".join(_char_pattern(c) for c in word) for word in words if word)
    found = re.search(pattern, passage) if pattern else None
    if not found:
        return esc(passage)
    return esc(passage[:found.start()]) + "<mark>" + esc(found.group()) + "</mark>" + esc(passage[found.end():])


def claim_table(draft, pack):
    """{"1": {"claim", "source", "url", "fetched", "passage_html"}} for the source drawer."""
    passages = {f"P{p['id']}": p for p in pack["passages"]}
    table = {}
    for claim in draft["claims"]:
        passage = passages[claim["passage"]]
        table[claim["id"][1:]] = {
            "claim": claim["text"], "source": passage["source"], "url": passage["url"],
            "fetched": passage["fetched_at"][:10], "passage_html": mark_quote(passage["text"], claim["quote"])}
    return table


def sections_html(sections):
    return "".join(f"<h3>{esc(s['heading'])}</h3>{render_text(s['text'])}" for s in sections)


def depth_texts(draft):
    brief = "\n".join(draft["brief"])
    editorial = " ".join(s["text"] for s in draft["editorial"])
    deep = " ".join(s["text"] for s in draft["deep_dive"])
    return brief, editorial, deep
