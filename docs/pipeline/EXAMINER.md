# Examiner

Status: built and run on real drafts, 1 November 2026. Code: `steelframe/pipeline/examiner.py`, `rubric.py`.

## What this is for

The Examiner scores a draft against the [quality rubric](../QUALITY_RUBRIC.md), the same eight dimensions a human reviewer would use. The score decides whether a draft goes back for a rewrite, and feeds the publish gate.

## Terms

| Term | Meaning |
|---|---|
| Dimension | One thing the rubric scores, such as Accuracy or Judgment, from 1 to 5 |
| Weight | How many of the 100 points a dimension carries |
| Weakness | A short fix the Examiner suggests. A failing draft goes back to the Writer with these |

## How it works

| Step | Who | What happens |
|---|---|---|
| 1 | Code | Build the prompt: the brief, editorial, deep dive, Mains question, claims, the fact-check result, and the syllabus topic with its count of past questions |
| 2 | Model | A model from a different provider than the Writer scores each dimension 1 to 5 with a short reason, and lists up to five weaknesses |
| 3 | Code | Checks the shape (all eight keys, whole numbers 1 to 5) |
| 4 | Code | Adds up score ÷ 5 × weight for each dimension, and applies the pass rules |

**The model never decides pass or fail.** Code does. A draft passes when the total is at least 70 and Accuracy is above 2.

A test reads the weights out of `docs/QUALITY_RUBRIC.md` and fails if the code and the document disagree.

## Example

| Dimension | Weight | Score | Points |
|---|---|---|---|
| Accuracy | 25 | 5 | 25 |
| Judgment | 20 | 4 | 16 |
| Evidence quality | 10 | 5 | 10 |
| Exam fit | 10 | 5 | 10 |
| Linking | 10 | 3 | 6 |
| Consistency | 10 | 5 | 10 |
| Readability | 10 | 4 | 8 |
| India link | 5 | 3 | 3 |
| **Total** | **100** | | **88, pass** |

This is the real score of the 31 October tax devolution draft.

## What the first run showed

| Draft | Total | Note |
|---|---|---|
| Tax devolution (31 Oct) | 88 | Linking and India link scored 3 |
| MoHUA workshop on a clean Delhi | 91 | |
| BIMSTEC maritime exercise | 91 | |

All three scored in the high 80s. The weaknesses the Examiner listed were sensible (add the Finance Commission, link past questions, add data), so the scoring is useful for rewrites. **But a free model scoring a free model's draft is probably too kind.** A first prompt gave 85 to 91, and telling it to start every dimension at 3 and justify any raise moved the numbers only 1 to 3 points. There are no human scores to calibrate against yet, so the 70 bar cannot be trusted as a measure of "better than coaching material". It works as a floor against bad drafts, not as proof of quality.

## Choices considered

| Option | For | Against | Verdict |
|---|---|---|---|
| A. A different model scores each dimension, code adds up | Cheap. Reasons are readable. The rubric stays in the document | Models score generously | **Chosen**, with calibration against humans left open |
| B. The Writer scores its own draft | One fewer call | Marks its own homework | Ruled out |
| C. Pairwise: ask which of two drafts is better | Models are better at comparing than scoring | Needs a reference piece for every issue, which we do not have in the daily run | Use in the bake-off only |
| D. Several examiners, take the median | Less noise | Two or three times the quota | Not now |

## What can go wrong

| Risk | Response |
|---|---|
| Too kind | Compare with blind human scores in the evaluation phase and tune the prompt until they agree. The pass bar may need to rise |
| Reasons that do not match the scores | Reasons are kept with the scores so an auditor can read them |
| A bad answer shape | Rejected, next model tried |
| Examiner and Writer share a provider | The router is told to skip the Writer's provider; the model is recorded with the score |

## Still open

| Question | Notes |
|---|---|
| Calibration to human scores | Needs 3 to 5 real reviewers (see `BLIND_REVIEW.md`) |
| Linking is scored on topic and counts only | Past-question text is not stored, so the Examiner cannot judge whether a question really matches a point |
