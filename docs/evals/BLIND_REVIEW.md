# Blind Review Protocol

Status: draft 0.1. The review has not been run. It needs real reviewers, who are not yet recruited.

## What it is

Reviewers read pairs of editorials on the same issue, one from Steelframe and one from established coaching material, without knowing which is which. They score each piece with the [quality rubric](../QUALITY_RUBRIC.md). The result tells us whether Steelframe's writing is good enough to continue.

## Why blind

If a reviewer knows a piece is machine-written, or knows it comes from a famous brand, the score changes. Hiding the source makes the scores about the writing.

## Who reviews

| Question | Answer |
|---|---|
| Who counts as a reviewer? | A serious aspirant (cleared Prelims at least once, or preparing for Mains) or a teacher who has coached for UPSC. We want both |
| How many? | Six reviewers. Each scores 10 of the 20 issues, so each issue gets three reviews, as the rubric requires |
| Are they paid? | To be decided. Reviewing is about eight hours of work, so an honorarium is expected |
| Can the project team review? | No. The people who built the pipeline cannot score its output |
| Conflicts | A reviewer who works for a publisher whose piece is in the benchmark is not assigned that issue |

## Materials

| Item | Detail |
|---|---|
| The pairs | 20 issues from the [benchmark set](BENCHMARK_SET.md), one Steelframe piece and one reference piece each |
| Blinding | Both pieces are rewritten into one plain layout: same fonts, headings as plain text, tables kept, branding and publisher names removed, dates written one way. Images and infographics are removed from both, and reviewers are told that visuals are not being scored |
| Labels | Each pair is shown as piece A and piece B. The assignment to A or B is randomised for each reviewer and issue |
| Order | The order of issues is randomised for each reviewer |
| Forms | [Scores](forms/review_scores_template.csv) and [preference](forms/review_preference_template.csv) templates |

Content is never edited to match the other piece. Only layout changes.

## Scoring

1. Read the whole piece, without skimming.
2. Score the seven dimensions below from 1 to 5, using the rubric's score descriptions.
3. Note the time spent and guess where the piece came from (Steelframe, coaching material, or unsure).
4. Repeat for the second piece of the pair.
5. Say which of the two you would rather study from, and why, in one sentence.

| Dimension | Scored by the reviewer |
|---|---|
| Judgment, Evidence quality, Exam fit, Linking, Consistency, Readability, India link | Yes |
| Accuracy | **No.** A reviewer cannot check every claim. Accuracy comes from the separate [accuracy audit](ACCURACY_AUDIT.md). The reviewer may note any claim that looks wrong, which is sent to the audit |

## Before the real review: a calibration round

1. Each reviewer scores the same two practice pairs, alone.
2. The team computes agreement between reviewers for each dimension (Krippendorff's alpha, ordinal).
3. Reviewers meet, compare scores and discuss the gaps. Score descriptions that caused disagreement are rewritten.
4. Practice pairs are scored again. The real review starts only when agreement is at least 0.667 on every dimension, as proposed in the rubric. Dimensions below that are fixed first.

## Conditions

| Rule | Why |
|---|---|
| Two weeks to finish, in the reviewer's own time | Keeps it realistic and avoids fatigue |
| No talking to other reviewers about the pieces until all scores are in | Keeps scores independent |
| No AI tools to help read or score | Reviews must be human |
| Score each piece straight after reading it | Memory fades |
| Breaks between pieces are fine | Tired reviewers score poorly |

## Analysis plan

The plan is set before any scores are seen.

| Question | Method |
|---|---|
| Does Steelframe beat the reference? | For each issue, the average weighted total of the Steelframe piece minus the reference piece. Count the issues where it is higher. The rubric asks for 14 of 20 |
| How big is the difference? | The mean paired difference, with a bootstrap confidence interval |
| Where is it stronger or weaker? | The same difference, per dimension |
| Do reviewers agree? | Krippendorff's alpha per dimension, with a confidence interval |
| Do the rubric scores match what reviewers would choose? | Compare each total with the stated preference, across all pairs |
| Was the blinding good? | The share of guesses that were right. If most reviewers guess correctly, the blinding failed and the results are weaker |
| Does one reviewer drive the result? | Re-run with each reviewer removed in turn |
| What counts as a pass? | The three rules in the rubric's "better than" test, applied to the combined scores, with Accuracy from the audit |

## Data and ethics

| Topic | Rule |
|---|---|
| Consent | Reviewers are told the purpose and agree to take part. They may stop at any time |
| Identity | Scores are stored under a code such as R01. The key linking codes to names is kept privately and never published |
| Reference text | Reviewers get the reference pieces for this evaluation only, and may not copy or pass them on |
| What is published | Aggregated results and the protocol. Individual scores are published only without names |

## What is still open

| Question | Notes |
|---|---|
| Recruiting six reviewers and finding the money for an honorarium | An evaluation-phase task |
| Whether reviewers may see the reference pieces under the publishers' terms | Needs checking before the first review |
| Whether visuals should be scored in a later round | They matter to readers. This round tests the writing |
| Whether three reviews per issue is enough | Check agreement in the calibration round |
