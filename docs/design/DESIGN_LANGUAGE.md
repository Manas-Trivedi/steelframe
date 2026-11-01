# Design language

Status: draft 0.1, 1 November 2026. Tokens: `site/assets/tokens.css`. Contrast tests: `tests/test_design.py`.

## What this is for

The rules for type, colour, space and motion, so every screen looks like one product. The values are in one CSS file that the site uses directly. The feel they serve is in [DESIGN_DIRECTION.md](DESIGN_DIRECTION.md).

## Terms

| Term | Meaning |
|---|---|
| Token | A named value, such as `--ink`, used everywhere instead of a raw colour |
| Step | One size on the type scale. Each is 1.2 times the one before |
| Contrast ratio | How different text is from its background, from 1 (none) to 21 (black on white). WCAG AA asks for 4.5 on body text |

## Type

| Role | Font | Why |
|---|---|---|
| Body and headings | A serif system stack: Iowan Old Style, Charter, Palatino, Georgia | Reads like print. Already on the device, so no download, no tracking, works offline |
| Interface (buttons, labels, margin) | The device's own sans-serif | Clear at small sizes. Zero download |

| Step | Size | Used for |
|---|---|---|
| -1 | 0.83 rem | Margin notes, captions, labels |
| 0 | 1.19 rem (19 px) | Body text. Line height 1.65 |
| 1 | 1.43 rem | Section headings |
| 2 | 1.71 rem | Page headings |
| 3 | 2.05 rem | The title of a piece |

The line is at most 66 characters wide, which suits long reading. Text sizes are in `rem`, so enlarging the browser text works.

**No web fonts.** A font download costs data and time on a weak phone and lets a font host see every reader. The cost is that the look differs a little between devices. Accepted.

## Colour

| Token | Light | Dark | Used for |
|---|---|---|---|
| bg | #faf8f3 | #131211 | Page, a warm paper tone |
| surface | #ffffff | #1c1b19 | Cards, the source drawer |
| ink | #1c1b19 | #ece8df | Body text |
| muted | #5b574f | #a8a298 | Secondary text |
| line | #e3ded3 | #34312c | Rules and borders |
| accent | #1f3a5f | #9dbce8 | Links, the claim underline, focus ring |
| highlight | #ffe9a8 | #4a3d0c | The reader's highlights, the quoted words in a source |
| good | #1e6b3a | #7fcf9a | A correct recall answer |
| bad | #a12b2b | #f08c8c | A wrong recall answer, a correction notice |

Every text pair that appears in the product is tested for 4.5 to 1 in both themes. **Colour never carries meaning alone.** A correct answer also says "Correct", a claim is underlined with dots, not only tinted.

## Space and shape

Spacing steps are 4, 8, 16, 24 and 40 px. Corners are 6 px. There are no shadows. Depth is shown with a thin line.

## Motion

| Where | What | Time |
|---|---|---|
| Source drawer opens | Slides up from the bottom | 200 ms |
| Depth switch | The text fades between depths | 120 ms |
| Map zoom | Eases to the chosen topic | 320 ms |
| Anywhere else | None | |

When the reader's device says "reduce motion", all durations become 0.

## Choices considered

| Option | For | Against | Verdict |
|---|---|---|---|
| A. System fonts | No download, private, fast | Look varies by device | **Chosen** |
| B. One web font for the whole product | Identical look everywhere | Cost on slow networks, privacy, a licence to check | Ruled out for v1 |
| C. Self-hosted font only for headings | Some character | Same cost for little gain | Ruled out for v1 |
| D. Warm paper background | Softer for long reading | A little less crisp than white | **Chosen** |
| E. Pure white background | Maximum contrast | Harsh for long sessions | Ruled out |

## What can go wrong

| Risk | Response |
|---|---|
| A device has none of the serif fonts | Falls back to Georgia, then the browser's serif. Still readable |
| Colours look different on a cheap screen | Contrast margins above 4.5 where possible. Test on a low-end phone in the beta |
| The look reads as dull | See the open question in the direction note |

## Still open

| Question | Notes |
|---|---|
| Real-device check of the serif stack and the colours | Needs a low-end Android phone |
| Print stylesheet | Aspirants may print. Not built |
