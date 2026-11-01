# Backfill: filling the site with past articles

## What it is for

A new site has almost nothing on it, and the daily run writes at most 3 articles a day. The backfill writes articles for the past 29 days, once, so an aspirant who arrives today finds a month of material and the site does not look as if it started today. When the days are filled it is simply not run again (unless the maintainer starts it).

## Words used here

| Word | Meaning |
|---|---|
| Release | One press release from PIB (the government's press office) or RBI (the central bank) |
| Archive ingest | Fetching past days' releases from the PIB and RBI archive pages (`steelframe/scout/archive.py`) |
| Triage | Scoring each release 0 to 3 for exam relevance. 2 or more is "kept" |
| Fresh item | A release dated within the last 3 days |
| Archive item | A release older than that |
| Release day | The Indian calendar day on which a release was published |

## How it works

| Step | How to run it | What happens |
|---|---|---|
| 1. Fetch the past | `python3 -m steelframe.scout.archive --days 30`, once | Past releases are stored with their real dates |
| 2. Score them | GitHub: Actions, daily, stage `triage`, with a limit | Every unseen release gets a relevance score. Nothing is written |
| 3. Write the best | GitHub: stage `backfill`, with a count. Repeat until done | For each release day in the last 29 days, up to 10 articles: best relevance first, one per topic per day. The site is rebuilt |

Every article goes through the same checks as a daily one. A piece that fails the gate is held, not published.

## The key idea: spread over days, no caps

| Setting (`config/gate.json`) | Value | Meaning |
|---|---|---|
| `backfill_days` | 29 | How far back to go |
| `backfill_per_day` | 10 | Most articles for any one release day |
| `daily_issue_cap` | 3 | The scheduled run's own cap, unchanged |
| `monthly_issue_cap` | 300 | Applies to the scheduled run only |

The backfill has no daily or monthly cap. A run stops on its own when it has done `count` issues, when 80 minutes have passed, or when the free model quota is used up (it waits for the next run; it never rushes). The scheduled run only takes fresh items and the backfill only takes archive items, so one can never use the other's slots.

## Example run

1. The archive ingest stores 1,509 PIB and 178 RBI releases from October.
2. Triage scores them; 631 are kept (score 2 or 3).
3. A backfill run with count 40 picks the best 40 across the 29 days, never more than 10 for one day and never two on the same topic for one day. Say 36 publish and 4 are held.
4. The run is repeated, a few times a day as quota allows, until each day has up to 10 articles. On the current data that is about 236 articles over 26 days.
5. Each backfilled piece shows its release date (for example 15 October) and the tag "From the archive". Its web address uses the day it was written, so no link changes.

## Choices considered

| Choice | Picked | Other options | Why not the others |
|---|---|---|---|
| What to write | Best 10 per release day | (a) The best 250 overall. (b) Everything kept (631) | (a) Leaves some days empty and piles onto big news days. (b) About 2.5 times the quota and a slow site |
| Caps | None for the backfill, bounded by days, per-day count, time and quota | (a) The same caps as the daily run. (b) A daily cap just for the backfill | (a) 3 a day would take months for a one-off. (b) A cap would slow a job that is meant to finish |
| Fresh days | Left to the daily run | Backfill them too | Items under 3 days old count against the daily run's 3 slots, so the backfill would use them up |
| Trigger | Manual, repeated | A nightly schedule | A one-off: it should stop by itself once the days are full |
| Date on the site | Release date, with a tag | (a) The day written. (b) A separate Archive section | (a) Makes old news look new. (b) Hides the material the backfill exists to show |

## What can go wrong

| Risk | What happens |
|---|---|
| Free quota runs out mid-run | The remaining issues are deferred and the run exits with a warning. The next run continues |
| The job runs out of time | No new issue is started after 80 minutes, so a run is never cut off while saving |
| A model cannot write an item | After 3 runs in a row it is held, so it stops blocking the queue |
| The audit alarm trips | The backfill stops, as the daily run does |
| A bad batch is published | Fact-check and gate apply to every piece. Corrections work as for any article. Read the first batch before running many |
| Quiet days | Weekends and holidays have few kept items, so some days get fewer than 10 |

## Still open

| Question | Note |
|---|---|
| How many calls does one article cost? | Not measured. The first run should report it |
| The last 3 days | Covered only by the daily run's 3 a day. A one-off to fill them is possible |
| Quality | No human has read the writing yet. Read the first batch before running more |
