# Back-test Design

Status: draft 0.1. No back-test has been run. This describes how it will be run.

## What it is

A back-test asks a simple question about the past: **if Steelframe had been running before an exam, would its editorials have prepared an aspirant for what the exam then asked?**

We cannot ask this about the future. But past exam papers are public, and so is the news that came before them. So we can replay history.

## Why it matters

The project's first rule is to prove the writing works before building the app. A back-test is one of two proofs. The other is the [blind review](BLIND_REVIEW.md), which asks whether readers prefer the writing. The back-test asks whether the writing covers the right ground.

## Terms used here

| Term | Meaning |
|---|---|
| Prelims, Mains | The first (objective) and second (written) stages of the UPSC exam |
| Past question | A question from an earlier paper, tagged by topic in [the tagging notes](PAST_PAPER_TAGGING.md) |
| `ca` question | A past question tagged as needing recent news, roughly the last 18 months |
| Cutoff date | The day the exam was held. Only news before it may be used |
| Window | The stretch of time before the cutoff that we replay, here 18 months |
| Editorial | One Steelframe piece on one issue |
| Covered | A question counts as covered when the editorials published inside the window contain what is needed to answer it |
| Leakage | When knowledge from after the cutoff gets into the replay, which would make results look better than they are |

## Design decision: how to replay

| Option | How it works | For | Against |
|---|---|---|---|
| A. Full replay | Run the whole pipeline for every day of the window, then test the output against the questions | Truest picture of what would have happened | Costly: about 540 days of runs per exam. Slow. Needs the finished pipeline |
| B. Topic coverage | List the topics of the `ca` questions, then check whether an editorial on that topic would have been written before the cutoff | Cheap. Can start before the pipeline exists | Weak. An editorial on the right topic may still miss the fact asked |
| C. Answerability | Take only the editorials published before the cutoff, and test whether each `ca` question can be answered from them | Close to what an aspirant would gain. Tests facts, not topic labels | Needs editorials to exist, and needs a fair way to judge "answerable" |
| D. Staged: B first, then C | Use B now to see how much of the exam is even the kind of thing an editorial could cover. Use C once the pipeline exists, replaying fewer days (below) | Cheap early signal, honest later test | Two steps, and the early step is only a rough guide |

**Pick: D.** B alone overstates success, and A alone is too costly and blocks on the pipeline. Staging gives an early signal now and a firm answer later.

To keep C affordable, it replays a sample of days chosen to cover the window evenly, plus every day that a `ca` question's topic was in the news. The sampling rule is set before looking at results.

## Inputs

| Input | Where it comes from |
|---|---|
| Tagged questions | `data/past_papers/tags/`. Only the `ca` ones are used |
| A dated news record for the window | Official sources and newspapers for each day, each item stamped with its publication date. To be built in the knowledge-base phase |
| The pipeline's editorials | Produced by replaying the window |
| Cutoff dates | The exam dates, from UPSC's published calendars |

## Stage 1: topic coverage (can run now)

1. Take every `ca` question for a paper.
2. For each, write what a covering editorial would have needed to say, in one line, without looking at the answer options.
3. Search the dated news record for items published before the cutoff that match that line.
4. Mark the question: **findable** (the news was there before the cutoff), **late** (the news came after the cutoff, so the question was not predictable), or **absent** (no matching item).

This does not test the writing. It measures the ceiling: the best the pipeline could do if it caught every item.

## Stage 2: answerability (needs editorials)

1. Replay the pipeline over the sampled days, with access only to news dated before the cutoff.
2. Give an independent grader the question and the replay's editorials, and nothing else. The grader answers the question, or says it cannot be answered.
3. Compare the grader's answers to the official key.
4. Mark each question: **answerable and right**, **answerable but wrong**, or **not answerable from the editorials**.

The grader is a reviewer or a model. If a model, it is not the one that wrote the editorials, and it is told to rely only on the supplied text.

## What we measure

| Measure | Definition | Why |
|---|---|---|
| Ceiling | Share of `ca` questions marked findable in Stage 1 | How much of the exam the news could even have supplied |
| Coverage | Share of `ca` questions answerable and right in Stage 2 | What aspirants would have gained |
| Gap | Ceiling minus coverage | What the pipeline missed that it could have caught |
| Coverage by area | Coverage split by syllabus area (GS1 to GS4, Prelims-led) | Where the pipeline is weak |
| Wasted effort | Share of the editorials that no later question touched, by area | Rough guide only. Many good editorials are not asked about |

## Baselines and pass bar

| Comparison | Why |
|---|---|
| Random: pick the same number of topics at random | Shows coverage is not just luck |
| A reference product, where its archive for the window is available | Tests the "better than" claim. Needs permission and care over reuse. Optional |

Proposed pass bar, to settle with real reviewers: coverage at least 60% of the ceiling, and clearly above the random baseline, in every syllabus area that has at least 10 `ca` questions. These numbers are proposals.

## An example run

The example is illustrative.

| Step | What happens |
|---|---|
| 1 | The tags show a Prelims question on a space-technology item, tagged `G3.IT`, `ca = y`. |
| 2 | Stage 1 writes the line: "needs the name and purpose of a space mission launched in the months before the exam." |
| 3 | Search finds two official press releases dated four and seven months before the cutoff. The question is marked **findable**. |
| 4 | Stage 2: the replay produced an editorial on that mission. The grader reads only that editorial and answers the question correctly. Marked **answerable and right**. |
| 5 | Another question asks about a small item, such as a species or an index mentioned once in the news. No editorial covered it. Marked **not answerable**. The ceiling counts it as findable, so the gap grows by one. |

## What the pilot tags already suggest

Many `ca` questions in the two Prelims papers tagged so far ask about small items that were mentioned in the news: a species, a legal code, an index, a settlement. A daily editorial on a major issue does not cover these. If this holds across more years, the back-test will show a low coverage rate for editorials alone. This would not mean the writing is poor. It would mean the product also needs a short "in the news" layer of facts. That is flagged as an open question for the product, and the back-test is how we find out.

## What can go wrong

| Risk | Response |
|---|---|
| Leakage: a model answers from what it learned in training, not from the editorials | Use graders told to answer only from the supplied text. Test with questions on events after the grader's training cutoff, and with a check where the editorials are removed. If the grader still answers right, the result is not trusted |
| Tags are one person's judgment | A sample of tags is reviewed by a second person, and the disagreement rate is reported |
| "Findable" is a judgment | Two reviewers decide on a sample. Disagreements are settled by a third |
| Small number of papers | Report counts and ranges, not single percentages, and do not read trends into a few years |
| Cutoff dates are wrong | Take them from UPSC's own calendars and check against each paper's date |
| The window is too short or long | Run 12 and 24 months as well, to see if the answer changes |

## What is still open

| Question | Notes |
|---|---|
| Who is the grader, a person or a model? | A model is cheaper. A person is more trusted. Likely both on a sample |
| Is 60% of the ceiling the right bar? | Needs the first run to calibrate |
| Which years to replay first? | Suggested: the latest completed exam, then two earlier ones, once the dated news record exists |
| Do we add the "in the news" layer to the product? | Depends on Stage 2 results |
