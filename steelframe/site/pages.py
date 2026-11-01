"""Page templates. Plain functions that return HTML strings."""
from urllib.parse import urlencode

from .render import claim_table, esc, json_for_script, render_paragraph, render_text, sections_html

NOTICE = ("Steelframe is an independent project. It is not affiliated with, endorsed by, or connected to the Union "
          "Public Service Commission or any government body. Sources are linked on every claim.")


def page(site, title, body, root="", description=""):
    """root is the path back to the site root ("" for top-level pages, "../" for pieces)."""
    base = esc(root)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · {esc(site['title'])}</title>
<meta name="description" content="{esc(description or site['tagline'])}">
<link rel="stylesheet" href="{base}assets/tokens.css">
<link rel="stylesheet" href="{base}assets/style.css">
<script>document.documentElement.dataset.js = "1"; try {{ var t = localStorage.getItem("sf.theme"); if (t) document.documentElement.dataset.theme = t; }} catch (e) {{}}</script>
</head>
<body data-root="{base}">
<a class="skip" href="#main">Skip to the text</a>
<header class="site">
  <a class="brand" href="{base}index.html">{esc(site['title'])}</a>
  <nav aria-label="Main">
    <a href="{base}index.html">Today</a>
    <a href="{base}map.html">Map</a>
    <a href="{base}revision.html">Revision</a>
    <a href="{base}me.html">Me</a>
  </nav>
</header>
<main id="main">
{body}
</main>
<footer class="site">
  <p>{esc(NOTICE)}</p>
  <p><a href="{base}corrections.html">Corrections</a> · <a href="{esc(site['repo'])}">Source code and rubric</a> · Apache License 2.0</p>
</footer>
<script src="{base}assets/logic.js" defer></script>
<script src="{base}assets/app.js" defer></script>
</body>
</html>
"""


def issue_card(e, root=""):
    return f"""<article class="card">
  <p class="meta">{esc(e['date'])} · {esc(e['topic_name'])} · about {e['minutes']['editorial']} min</p>
  <h2><a href="{esc(root)}p/{esc(e['slug'])}.html">{esc(e['title'])}</a></h2>
  <p class="lead">{esc(_plain(e['draft']['brief'][0]))}</p>
  <p class="meter" aria-label="Relevance {e['relevance']} of 3"><span style="width:{e['relevance'] * 33.3:.0f}%"></span></p>
</article>"""


def _plain(text):
    from ..pipeline.checks import MARKER
    return MARKER.sub("", text).replace(" .", ".").strip()


def index_page(site, editorials):
    if editorials:
        cards = "\n".join(issue_card(e) for e in editorials)
        body = f"<h1>Today</h1>\n<div class=\"cards\">\n{cards}\n</div>\n<p class=\"end\">That is today.</p>"
    else:
        body = "<h1>Today</h1>\n<p class=\"end\">Nothing has been published yet.</p>"
    return page(site, "Today", body)


def month_page(site, month_label, editorials):
    cards = "\n".join(issue_card(e, "../") for e in editorials)
    body = f"<h1>{esc(month_label)}</h1>\n<p class=\"meta\">{len(editorials)} editorials</p>\n<div class=\"cards\">\n{cards}\n</div>"
    return page(site, month_label, body, root="../")


def months_index(site, months):
    items = "\n".join(f"<li><a href=\"m/{esc(key)}.html\">{esc(label)}</a> ({count} editorials)</li>" for key, label, count in months)
    body = f"<h1>Archive</h1>\n<ul class=\"plain\">\n{items}\n</ul>"
    return page(site, "Archive", body)


def editorial_page(site, e, past_links):
    draft = e["draft"]
    claims = claim_table(draft, e["pack"])
    brief_html = "<ul>" + "".join(f"<li>{render_paragraph(b)}</li>" for b in draft["brief"]) + "</ul>"
    quiz = []
    for n, q in enumerate(draft["recall_questions"]):
        options = "".join(
            f'<label><input type="radio" name="q{n}" value="{i}"> <span>{esc(o)}</span></label>'
            for i, o in enumerate(q["options"]))
        quiz.append(f'<fieldset class="q" data-q="{n}" data-answer="{q["answer"]}"><legend>{n + 1}. {esc(q["question"])}</legend>'
                    f'{options}<p class="explain" hidden>{esc(q["explanation"])}</p></fieldset>')
    mains = draft["mains_question"]
    approach = "".join(f"<li>{esc(a)}</li>" for a in mains["approach"])
    corrections = "".join(f'<p class="correction" role="note"><strong>Correction, {esc(c["date"])}:</strong> {esc(c["text"])}</p>'
                          for c in e.get("corrections", []))
    past = "".join(f'<li><a href="{esc(url)}">{esc(label)}</a></li>' for label, url in past_links) or "<li>None tagged yet</li>"
    issue_url = esc(f"{site['repo']}/issues/new?" + urlencode({
        "title": f"Error report: {e['title']}",
        "body": f"Piece: {e['slug']}\nClaim number or text:\nWhat is wrong:\nSource that shows it:"}))
    meta = {"slug": e["slug"], "title": e["title"], "date": e["date"], "topic": e["topic"]}
    body = f"""{corrections}
<article class="piece" data-meta="{esc(json_for_script(meta))}">
  <p class="meta">{esc(e['date'])} · {esc(e['topic_name'])}</p>
  <h1>{esc(draft['title'])}</h1>
  <div class="depths" role="group" aria-label="Reading depth">
    <button type="button" data-depth="brief">Brief <small>{e['minutes']['brief']} min</small></button>
    <button type="button" data-depth="editorial" aria-pressed="true">Editorial <small>{e['minutes']['editorial']} min</small></button>
    <button type="button" data-depth="deep">Deep dive <small>{e['minutes']['deep']} min</small></button>
    <button type="button" id="save" aria-pressed="false">Save</button>
  </div>
  <div class="layout">
    <div class="text" id="text">
      <section data-depth="brief" hidden>{brief_html}</section>
      <section data-depth="editorial">{sections_html(draft['editorial'])}</section>
      <section data-depth="deep" hidden>{sections_html(draft['deep_dive'])}</section>
      <section class="mains"><h2>Mains question</h2><p>{esc(mains['question'])}</p>
        <details><summary>Approach</summary><ul>{approach}</ul></details></section>
      <section class="recall"><h2>Recall questions</h2>
        <form id="quiz">{''.join(quiz)}<button type="submit">Check answers</button></form></section>
    </div>
    <aside class="margin" aria-label="Notes in the margin">
      <h2>Syllabus</h2>
      <p>{esc(e['topic_name'])}</p>
      <h2>Past questions</h2>
      <p>{len(past_links)} on this topic. Question text is not stored; the links open the official paper.</p>
      <ul>{past}</ul>
      <h2>Found a mistake?</h2>
      <p><a href="{issue_url}">Report an error</a></p>
    </aside>
  </div>
  <div id="drawer" class="drawer" role="dialog" aria-modal="false" aria-label="Source" hidden>
    <button type="button" id="drawer-close" aria-label="Close source">Close</button>
    <div id="drawer-body"></div>
  </div>
  <script type="application/json" id="claims">{json_for_script(claims)}</script>
</article>"""
    return page(site, draft["title"], body, root="../", description=_plain(draft["brief"][0])[:160])


def map_page(site, topics, counts, recent):
    """topics: [{"id","paper","name"}]; counts: {topic_id: n editorials in the last 30 days}; recent: {topic_id: [(title, href)]}."""
    papers = {"GS1": "General Studies I", "GS2": "General Studies II", "GS3": "General Studies III",
              "GS4": "General Studies IV", "PRE": "Other", "X": "Other"}
    groups = {}
    for t in topics:
        groups.setdefault(papers.get(t["paper"], "Other"), []).append(t)
    parts = []
    for paper, items in groups.items():
        tiles = []
        for t in items:
            n = counts.get(t["id"], 0)
            links = "".join(f'<li><a href="{esc(h)}">{esc(title)}</a></li>' for title, h in recent.get(t["id"], []))
            inner = f"<ul>{links}</ul>" if links else ""
            level = min(n, 4)
            tiles.append(f'<li class="tile level-{level}"><details><summary><span>{esc(t["name"])}</span> '
                         f'<b>{n}</b></summary>{inner or "<p>No editorials in the last 30 days.</p>"}</details></li>')
        parts.append(f"<h2>{esc(paper)}</h2><ul class=\"tiles\">{''.join(tiles)}</ul>")
    body = ("<h1>Syllabus map</h1>\n<p class=\"meta\">Each tile is a syllabus topic. The number is how many editorials touched "
            "it in the last 30 days. Open a tile to read them.</p>\n" + "\n".join(parts))
    return page(site, "Syllabus map", body)


def revision_page(site):
    body = """<h1>Revision</h1>
<p class="meta">Questions you missed come back after 1, 3, 7 and 14 days. They are kept in this browser only.</p>
<div id="revision"><p>Loading…</p></div>
<noscript><p>Revision needs JavaScript, because your answers are kept in your own browser.</p></noscript>"""
    return page(site, "Revision", body)


def me_page(site):
    body = """<h1>Me</h1>
<p class="meta">Everything on this page is kept in your own browser. There is no account and no sign-in. If you clear your browser data it is gone, so use <em>Download my data</em> now and then.</p>
<div id="me"><p>Loading…</p></div>
<noscript><p>This page needs JavaScript, because your data is kept in your own browser.</p></noscript>"""
    return page(site, "Me", body)


def corrections_page(site, corrections):
    if corrections:
        def name(c):
            return f'<a href="p/{esc(c["slug"])}.html">{esc(c["title"])}</a>' if c["slug"] else esc(c["title"]) + " (taken down)"
        rows = "".join(f'<tr><td>{esc(c["date"])}</td><td>{name(c)}</td><td>{esc(c["text"])}</td></tr>' for c in corrections)
        table = f'<table><thead><tr><th>Date</th><th>Piece</th><th>Correction</th></tr></thead><tbody>{rows}</tbody></table>'
    else:
        table = "<p>No corrections yet.</p>"
    body = f"""<h1>Corrections</h1>
<p class="meta">A correction is added here, dated, and shown at the top of the piece. Nothing is changed silently.</p>
{table}
<h2>Report an error</h2>
<p>Every piece has a "Report an error" link in its margin. It opens a form on <a href="{esc(site['repo'])}/issues">our issue tracker</a>.</p>"""
    return page(site, "Corrections", body)
