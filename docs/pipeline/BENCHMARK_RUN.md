# Benchmark run

Status: **partly done, 1 November 2026. The bar in the quality rubric is not tested and cannot be by software alone.**

## What this is for

The roadmap's last pipeline step reads: run the 20 benchmark topics, score them, and iterate until the bar is met. The bar is in the [quality rubric](../QUALITY_RUBRIC.md): Steelframe beats the coaching reference on at least 14 of 20 issues in blind review by at least three people, with no accuracy failure. This note says what was run, what the numbers mean, and what is missing.

## Terms

| Term | Meaning |
|---|---|
| Benchmark set | 20 topics from a coaching publisher's July 2026 monthly, listed in `data/benchmark/topics.csv` |
| Blind review | People score pieces without knowing which is whose ([BLIND_REVIEW.md](../evals/BLIND_REVIEW.md)) |
| Real issue | An issue built from a live PIB release the day it was fetched |

## What was run

| Run | Result |
|---|---|
| Full daily run on three real issues from 31 October 2026 | 3 published, all on attempt 1, Examiner totals 82, 88 and 89 |
| Code checks (quote, link, figure) on those drafts | All pass |
| Fact-check by a model on another provider | All 29 claims supported |
| Planted-error test of the Fact-checker | 3 of 3 caught |
| Automated audit by a third provider | 29 claims, 0 not fully supported |
| Writer bake-off, 7 models, 3 packs, 1 try each | No model passed the code checks on any pack that run (see [BAKEOFF.md](BAKEOFF.md)) |

## What was not run, and why

| Not run | Why |
|---|---|
| The 20 benchmark topics | They are July 2026 topics. The pipeline reads the live feed, so the July releases are not in the database, and no source has a way to fetch them by topic. Backfilling means finding each release by hand |
| The comparison with reference pieces | The reference text is private and the comparison needs at least three human reviewers for each piece. No reviewers exist yet |
| "Iterate until the bar is met" | There is no human score to iterate against. The Examiner is a free model scoring a free model, and it is generous (see [EXAMINER.md](EXAMINER.md)) |

**So the 70-point Examiner scores above are not evidence that Steelframe beats coaching material.** They show that the machinery works end to end and that its checks catch planted errors.

## What the real run does show

| Finding | Meaning |
|---|---|
| The checks catch what they are built to catch | Invented quotes, wrong figures and changed meanings fail the draft |
| First-try success is unreliable | The same model passed three of three in the daily run and failed two of three in the bake-off. The revision loop matters |
| One short release is thin evidence | The deep dives cannot add Acts or earlier years, because the figure check forbids unsourced numbers. This probably limits Judgment and Evidence scores more than anything the model does |
| Quota is the real limit | The Gemini free allowance was used up by testing in a day. Three issues a day needs about 25 to 60 calls |

## What is needed to finish this step

| Task | Who | Notes |
|---|---|---|
| Recruit 3 to 5 aspirants or teachers | Maintainer | The blind review protocol and forms are ready |
| Find PIB releases for the 20 topics | Maintainer or a helper | Searching PIB by title; add them to the database with a one-off script |
| Run the pipeline on them over several days | The scheduler | At 3 issues a day this takes a week. Raise the cap only if the quota allows |
| Score blind against the references | Reviewers | Then compare to the bar |
| Tune the Writer and Examiner prompts to the human scores | Maintainer | The Examiner's generosity is the first thing to fix |

## Still open

| Question | Notes |
|---|---|
| Does the writing beat coaching material? | Unknown. This is the project's riskiest assumption and it is still untested |
| Is a source of Acts, reports and earlier releases needed to reach the bar? | Probably. See the static base design |
