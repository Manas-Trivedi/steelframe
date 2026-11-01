# The site

Status: built 1 November 2026. Code: `steelframe/site/`, `site/assets/`. Build: `python3 -m steelframe.site.build`. **Not yet opened in a real browser** (no browser was available when it was built); the generator and the logic are tested, the look and the click behaviour are not.

## What this is for

The pages a reader sees: today's issues, a piece in three depths with a source behind every claim, a syllabus map, a revision queue, and a personal page. Stack reasons are in [STACK.md](STACK.md); look and feel in [the design notes](../design/DESIGN_DIRECTION.md).

## Terms

| Term | Meaning |
|---|---|
| Piece | One published editorial |
| Source drawer | The panel showing the exact passage behind a claim |
| Revision queue | Recall questions the reader got wrong, due again after 1, 3, 7 and 14 days |

## Pages

| Page | What it shows | Where its data comes from |
|---|---|---|
| Today (`index.html`) | The 20 newest pieces, with a one-line summary and a relevance bar | Database |
| Piece (`p/<date>-<id>-<title>.html`) | Brief, editorial, deep dive; Mains question; 3 recall questions; margin with the syllabus topic and past-question links; a "Report an error" link; any correction at the top | Database |
| Monthly (`m/2026-11.html`, `archive.html`) | Every piece of a month, and a list of months | Database |
| Map (`map.html`) | The 65 syllabus topics as tiles with the number of pieces in the last 30 days. Open a tile to see them. A flat view only (see [3D concepts](../design/3D_CONCEPTS.md)) | Database |
| Revision (`revision.html`) | Questions due today | The reader's browser |
| Me (`me.html`) | Streak and calendar, default depth, theme, saved pieces, highlights and notes, download and restore | The reader's browser |
| Corrections (`corrections.html`) | All dated corrections | Database |

## What the reader can do

| Action | How |
|---|---|
| Change depth | Three buttons. The choice is remembered |
| See a source | Tap or press Enter on an underlined sentence. The drawer shows the claim, the copied passage with the quoted words marked, the date it was copied, and a link to the original. Escape closes it |
| Answer recall questions | "Check answers" marks each as correct or not, with the explanation. Wrong ones join the revision queue |
| Highlight and add notes | Select a phrase inside one paragraph |
| Save a piece | The Save button |
| Back up | "Download my data" and "Restore from a file" on the Me page |

## What the build guarantees

| Guarantee | How it is checked |
|---|---|
| Only published pieces appear. A held piece never does, and a piece that stops being published disappears on the next build | Tests |
| Nothing a model wrote can inject markup. All text is escaped, and the data for the drawer cannot close its script tag | A test feeds `<script>` through every field |
| Each claim in the text maps to a stored passage | Tests |
| Revision dates and streaks are right | Node tests of the pure logic |
| Colours meet WCAG AA contrast in both themes | `tests/test_design.py` |

## What can go wrong

| Risk | Response |
|---|---|
| Never opened in a browser | First thing to do with a browser: open a piece, tap a claim, answer a question, check both themes and a phone width |
| A highlight that spans two paragraphs | Not supported; the bar does not appear |
| Browser data cleared | Backup button, said plainly on the Me page |
| A sentence is underlined wrongly | The underline covers the text before the marker back to the last full stop. A sentence with an internal full stop (an abbreviation) is underlined from after that stop |

## Still open

| Question | Notes |
|---|---|
| Real-device and real-browser test | Needed before the beta |
| Print style is minimal | Hides controls only |
| Search | Not in v1 |
