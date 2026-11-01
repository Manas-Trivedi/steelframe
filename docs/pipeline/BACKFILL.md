# Backfill: filling the site with past articles

## What it is for

A new site has almost nothing on it, and the daily run writes at most 3 articles a day. The backfill writes articles for older releases (the "archive") so an aspirant who arrives today finds a month of material, not two pieces. Limits, set by the maintainer: **at most 10 articles a day and 300 a month**.

## Words used here

| Word | Meaning |
|---|---|
| Release | One press release from PIB (the government's press office) or RBI (the central bank) |
| Archive ingest | Fetching past days' releases from the PIB and RBI archive pages (`steelframe/scout/archive.py`) |
| Triage | Scoring each release 0 to 3 for exam relevance. 2 or more is "kept" |
| Fresh item | A release dated within the last 3 days |
| Archive item | A release older than that |
| Lane | Fresh or archive. Each lane has its own daily cap |

## How it works

| Step | Command (GitHub: Actions, daily, Run workflow) | What happens |
|---|---|---|
| 1. Fetch the past | `python3 -m steelframe.scout.archive --days 30` | Past PIB and RBI releases are stored with their real dates. Run once, on a copy of the database |
| 2. Score them | stage `triage`, with a limit | Every unseen release gets a relevance score. Nothing is written or published |
| 3. Write the best | stage `backfill`, with a count | The best kept archive items are researched, written, fact-checked, scored and gated. The site is rebuilt |

The checks are the same as for a fresh article. The backfill never skips a check to go faster, and a piece that fails the gate is held, not published.

## The key idea: two lanes

| Lane | Daily cap | Picks |
|---|---|---|
| Fresh | 3 | Items from the last 3 days |
| Archive | 7 | Older items, best relevance first |
| Both | 10 a day, 300 a month | |

3 + 7 = 10, so the daily limit holds without the two runs knowing about each other. The scheduled run only takes fresh items, so a backfill day can never use up the slot for today's news. Held items count against the caps because they still used model quota.

## Example run

1. The archive ingest stores 1,509 PIB and 178 RBI releases from October.
2. Triage scores them: 631 are kept (score 2 or 3).
3. The maintainer starts the backfill with count 10. The archive lane has 7 slots, so at most 7 are decided; say 6 publish and 1 is held by the gate.
4. The site is rebuilt. Each backfilled piece shows its release date (for example 15 October) and the tag "From the archive". Its web address still uses the day it was written, so no link ever changes.
5. Next day, the scheduled run writes up to 3 fresh articles, and the backfill can run again for 7 more.

At 7 a day, the 631 kept items take about 3 months, and the 300-a-month cap is never the limit unless the daily runs are all used.

## Choices considered

| Choice | Picked | Other options | Why not the others |
|---|---|---|---|
| Caps | Separate daily cap per lane, one monthly cap | (a) Raise the single daily cap to 10. (b) Run the backfill only when the daily run is done | (a) The daily run picks the highest relevance first, so old items would crowd out the day's news. (b) Needs the two runs to know about each other |
| How an item is classed | By its date, 3 days back | (a) A flag set when the item is stored. (b) By the workflow that wrote it | (a) Needs a database change and a fix-up of old rows. (b) An article's lane would depend on which button was pressed |
| Date on the site | The release date, with a tag | (a) The day it was written. (b) A separate Archive section | (a) Makes old news look new. (b) Hides the material the backfill exists to show |
| Trigger | Manual, a few times | A nightly schedule | A schedule would spend free quota every day with nobody checking the output. Switch to a schedule once a manual run looks good |

## What can go wrong

| Risk | What happens |
|---|---|
| Free quota runs out mid-run | The remaining issues are deferred, not rushed. The run exits with a warning and the next run continues |
| A model cannot write an item | After 3 runs in a row it is held, so it stops blocking the queue |
| The audit alarm trips | The backfill stops, as the daily run does |
| A bad batch gets published | The fact-check and gate apply to every piece. Corrections work as for any article |
| Old news reads as stale | Each piece shows its date and the archive tag. Whether aspirants want old articles at all is unknown |

## Still open

| Question | Note |
|---|---|
| Are 10 a day and 300 a month right? | Set by the maintainer, who is not an aspirant. Review after a beta |
| How many calls does one article cost? | Not measured. The first runs should report it |
| A 15-day gap: archive pieces older than the exam cycle may not help | Decide how far back to go after reading the first results |
