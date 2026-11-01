# Design direction

Status: draft 0.1, 1 November 2026. Written without a design discussion, from the [product definition](../PRODUCT.md). Every choice marked "assumption" should be checked with real aspirants.

## What this is for

Steelframe is read, not browsed. This note fixes the feel of the product and how a reader moves through a piece, so the visual language ([DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md)) and the build have one target.

## Terms

| Term | Meaning |
|---|---|
| Depth | How much of a piece the reader sees: brief, editorial or deep dive |
| Claim | One sourced fact. It carries a faint underline in the text |
| Source drawer | The panel that opens when a claim is tapped, showing the exact passage, its date and a link |
| Margin | The side column with the syllabus topic and the past-question count. On a phone it moves below the title |
| Measure | The width of a line of text, counted in characters |

## The feel

| We want | We avoid |
|---|---|
| Calm and scholarly. Like a good printed editorial | Ads, banners, pop-ups, anything that competes with the text |
| Plain and precise. The text is the interface | Decoration for its own sake. Gradients, shadows, glass effects |
| Quiet progress: a streak calendar, not a score shouted at the reader | Streak guilt, red badges, "you will lose your streak" |
| Honest about uncertainty: a held or corrected piece says so | Hiding corrections |
| Fast on a cheap phone on a slow network | Heavy scripts, web fonts, large images |

## What we take from elsewhere

| Reference | What we take | What we leave |
|---|---|---|
| Print editorials (the broadsheet page) | A narrow column, a serif face, generous line spacing | Dense multi-column layouts that need a wide screen |
| Wikipedia hover cards | Showing a source without leaving the page | Cluttered link styling |
| Anki | Return missed questions after a few days | The heavy settings screen |
| Readwise Reader and Kindle | Highlights and notes kept with the text, calm reading view | Account walls |
| Duolingo | A visible daily habit | Loss-framed nudges and notifications |
| Hypothesis | Annotations anchored to exact text | Public annotation layers |

These are named for orientation. We have not tested any of them with aspirants.

## The reading experience

| Part | Behaviour |
|---|---|
| Today | Up to 3 issues a day at first. Each shows title, topic, read time and a small relevance bar. It ends with "That is today." |
| Depth switch | Three buttons at the top: Brief (about 1 min), Editorial (about 4 min), Deep dive (about 8 min). The choice is remembered. All three come from the same claims, so figures never differ |
| Claims | A faint dotted underline. Tap or press Enter to open the source drawer |
| Source drawer | Shows the exact passage with the quoted words marked, the source name, the fetch date and a link to the original. Close with Escape |
| Margin | Syllabus topic, number of past questions on it, and a "report an error" link |
| End of piece | The Mains question with an approach, then three recall questions. A wrong answer is queued for revision |
| Highlights and notes | Select text, add a note. Kept in the browser |
| Corrections | A visible, dated line at the top of a corrected piece |

Reading times assume 200 words a minute (assumption, to check with aspirants).

## Accessibility

| Rule | Why |
|---|---|
| Text and background pairs meet WCAG AA contrast (4.5 to 1), tested in code | Readable in daylight on a cheap screen |
| Everything works from the keyboard | Screen readers and keyboard users |
| Meaning never rests on colour alone: the claim underline is a pattern, not only a hue | Colour-blind readers |
| Motion respects the reader's "reduce motion" setting | Vestibular comfort |
| Text can be enlarged to 200 percent without breaking the layout | Low vision |
| Light and dark themes follow the device | Night reading |

## What can go wrong

| Risk | Response |
|---|---|
| The calm look reads as plain next to coaching sites with rich visuals | Compete on trust and clarity, not decoration. Test with aspirants before adding anything |
| Reading times are wrong | Show them as "about", compute from word count, correct after the beta |
| Source drawers on a small phone cover the text | Draw the drawer from the bottom, half height, with the claim still visible above it |

## Still open

| Question | Notes |
|---|---|
| Does a serif body suit this audience on phones? | Assumption: yes. Test with 5 aspirants |
| Hindi and regional scripts | Out of v1. The type scale must be checked when added |
| Product name and mark | "steelframe" is a working name. No logo yet |
