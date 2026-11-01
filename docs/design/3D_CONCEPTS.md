# 3D concepts

Status: draft 0.1, 1 November 2026. Nothing here is built. The v1 site uses flat views only (see the decision at the end).

## What this is for

The brief allowed "possibly 3D". Three-dimensional graphics help only if the third dimension carries information. This note tests each idea against one question: **what would a reader learn from the depth that a flat picture cannot show?** An idea with no answer is dropped.

## Terms

| Term | Meaning |
|---|---|
| three.js | A free library that draws 3D in the browser through WebGL |
| WebGL | The browser's way of using the graphics chip |
| Frame rate | Pictures drawn per second. 30 is the lowest that feels smooth |
| Low-end phone | A budget Android phone, taken here as 2 GB of memory and 4 slow cores |

## Concepts

| # | Idea | What the depth shows | Study reason | Verdict |
|---|---|---|---|---|
| 1 | **Syllabus map with time as depth.** Each syllabus topic is a point. Left and right group the four GS papers. Depth is the week the news touched it, so a topic that keeps returning forms a column | How long a topic has stayed in the news. A flat map shows only "now" | Spots topics that are warm for months, which exams reward | Worth testing after v1. A flat heat strip shows the same data more cheaply, so the 3D must beat it in a test with aspirants |
| 2 | **India map with extruded bars.** The height of a bar is the amount for each State, for example the tax devolution table | Nothing the flat map lacks. Heights are harder to compare than a sorted list | None. Reading exact numbers matters more | Dropped |
| 3 | **Constitution as a layered model.** Parts and Schedules stacked as floors | Layout only | A memory aid for one-off structure, not for current affairs | Dropped |
| 4 | **Link graph of an event.** One event joined to the topics, Acts and past questions it touches, pulled apart in 3D | How many topics one event touches, and how closely | A single event often reaches four or five topics. That is exactly how Mains answers are built | Worth testing as a 2D graph first. 3D adds spin and hides labels |

Concepts 1 and 4 survive. In both, **a flat version must exist first**, because the flat version is what weak phones and screen readers get.

## Low-end phone plan

| Rule | Value | How it is checked |
|---|---|---|
| Script weight | At most 150 KB over the network for the whole 3D feature | Build report |
| Frame rate | At least 30 frames a second with the browser's CPU slowed 4 times | Browser performance panel. Not run yet |
| Memory | Fewer than 150 draw objects (about 65 topics plus labels) | Count in code |
| Fall back to flat when | WebGL is missing, the device reports 2 GB of memory or less, or fewer than 4 cores, or the reader chose "reduce motion" | Feature test in code |
| Same information | Every fact shown in 3D is in a list below it | Review |
| Keyboard and screen reader | The list is the accessible version | Review |

## Decision

**v1 ships flat only.** The syllabus map is a tile view with the same data (see the site build). Reasons:

| Reason | Detail |
|---|---|
| The evaluation phase is about writing quality | The product definition says the app waits for the writing to beat the benchmark. 3D does not help that |
| Weight and risk | The library alone is a large download for the poor networks this audience often has |
| No evidence yet | Whether aspirants prefer the 3D map is untested |

Concept 1 returns after the beta, if readers ask for more from the map.

## What can go wrong

| Risk | Response |
|---|---|
| 3D becomes a toy that slows reading | The fall-back rules and the "flat first" rule |
| Motion sickness | Motion off when the reader asks, no auto-spin |
| Labels unreadable in 3D | Labels always drawn flat, facing the reader |

## Still open

| Question | Notes |
|---|---|
| Does concept 1 beat a flat heat strip in a test with aspirants? | Needs 5 or more aspirants |
| Frame rate on real hardware | Needs a low-end Android phone |
