# Benchmark Set

Status: draft 0.1. The topics are chosen. No Steelframe editorials exist yet, so no pairs are complete.

## What it is

The benchmark is a fixed list of 20 issues. For each, we gather one editorial from established coaching material (a **reference piece**) and, later, produce one Steelframe editorial. The pairs are what reviewers compare in the [blind review](BLIND_REVIEW.md). The list is in `data/benchmark/topics.csv`.

## Why a fixed list

If the topics changed from run to run, any improvement could be luck. A fixed list means we can improve the pipeline, run it again on the same 20 issues, and see whether the scores moved.

## How the 20 topics were picked

1. **Spread across the syllabus.** The list follows the weight of the General Studies papers, so that no one area dominates.
2. **Real, recent issues** from the months before this document, each one with a reference piece we have actually seen.
3. **A mix of types:** a new law, a committee report, a scheme, a summit, an index, a technology item, a heritage listing.

| Area | Topics | Syllabus paper |
|---|---|---|
| Polity and governance | 4 | GS2 |
| International relations | 3 | GS2 |
| Economy | 4 | GS3 |
| Environment | 3 | GS3 |
| Science and technology | 2 | GS3 |
| Security | 2 | GS3 |
| Social issues | 1 | GS2 |
| Culture | 1 | GS1 |

The full list, with the syllabus topic id of each and where its reference piece comes from, is in `data/benchmark/topics.csv`.

## Rules for pairing

| Rule | Why |
|---|---|
| One reference piece per topic, from established coaching material | Gives a fair comparison point |
| Where more than one publisher covers a topic, the reference is picked by a seeded random draw, not by hand | Stops us choosing a weak reference to flatter ourselves |
| The reference must be dated within 30 days of the news | Keeps the facts comparable |
| The Steelframe editorial is written as of the reference's date, using only sources dated up to then | The two pieces must know the same things |
| Neither piece may be edited to match the other's format by changing its content | Only layout is normalised, and only for blinding |
| Reference text is stored privately and is never published. The repository holds only the publisher, title, section and date | The reference material belongs to its publishers |

## What is deliberately not in the list

- **Topics we cannot find a reference for.** A topic with no reference piece cannot be a pair.
- **Hindi pieces.** Hindi is out of scope for the first version.
- **Pure facts items** such as news in shorts. These test a different thing, discussed in the [back-test design](BACKTEST.md).

## A caution about the list

Most of the 20 topics come from one monthly publication. That means the list reflects what one publisher thought mattered. It is a convenient start. It could make the benchmark favour the topics that publisher covers well. Before the first blind review, replace some of the entries with topics chosen from the past-question tags, so that the list also reflects what the exam has actually asked. The draft is marked accordingly.

## What is still open

| Question | Notes |
|---|---|
| Is 20 the right size? | Enough to run the proposed "14 of 20" test in the [rubric](../QUALITY_RUBRIC.md). A pilot may show we need more |
| Which publisher is the reference for each topic, where several exist? | Settled by the seeded draw, once all candidate pieces are collected |
| Should some topics come from the exam's own past questions? | Probably yes, see the caution above |
| Can we show the pairs to reviewers without breaching the publishers' rights? | Needs checking. Reviewing for evaluation may be permitted, but the pieces must not be published or passed on |
