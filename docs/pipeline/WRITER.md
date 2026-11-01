# Writer

Status: built and run on real evidence packs, 1 November 2026. Code: `steelframe/pipeline/writer.py`.

## What this is for

The Writer turns one evidence pack into the product: a set of **sourced claims**, three reading depths built from those claims, one Mains question and three recall questions. It does not check its own work. The [Fact-checker and code checks](CHECKS.md) do that.

## Terms

| Term | Meaning |
|---|---|
| Claim | One fact, figure, date or decision, with an exact quote and the id of the passage that holds it |
| Brief, editorial, deep dive | The three reading depths: about 120, 600 and 1,000 words |
| Marker | A tag like `[c3]` after a sentence, pointing at claim c3 |
| Recall question | A Prelims-style question with four options, answerable from the claims |

## How it works

| Step | What happens |
|---|---|
| 1 | Take complete evidence packs that have no draft yet (up to 3 a run) |
| 2 | Send the passages, the topic list and the rules. Route `writer` in `config/models.json` |
| 3 | The model replies with one JSON object |
| 4 | Code checks the shape: 3 to 25 claims numbered c1, c2, ...; each claim names a passage that is in the pack; every marker points at a real claim; section counts and minimum lengths; exactly 3 recall questions with 4 options and an answer 0 to 3 |
| 5 | A bad shape is rejected and the router tries the next model. The draft is saved only when it passes |

**Why the depths cannot disagree.** Each depth cites the same claims by id. The [figure check](CHECKS.md) later confirms that every number in the text appears in a claim.

## Rules given to the model

| Rule | Why |
|---|---|
| Use only the passages. Add no fact, number or date | A claim without a source cannot ship |
| Quote exactly, character for character | The quote check is done by code |
| Analysis may be added but must not carry new figures | Judgment is scored in the rubric, and figures are what go wrong |
| If the passages are thin, write less | Padding with invented background is worse than a short piece |

## Choices considered

| Option | For | Against | Verdict |
|---|---|---|---|
| A. One call returns claims, depths and questions as JSON | One call. Depths share claims. Checks run on data | One long answer. A cut-off answer is useless | **Chosen**, with a large token allowance (16,000) because reasoning models spend part of it thinking |
| B. Separate calls for claims, then each depth | Smaller answers | 4 or more calls per issue, and the depths can drift apart | Ruled out: quota |
| C. Free text, parsed afterwards | Easy to prompt | Claim and quote drift apart | Ruled out |

## What can go wrong

| Risk | Response |
|---|---|
| Quote altered or invented | Quote check in code, next stage |
| Claim says more than its quote supports | Fact-checker reads claim and passage together. Real example from the first run: one claim listed three States' amounts but quoted a row that shows only one |
| Answer cut off or not JSON | Rejected, next model tried |
| A rate-limited minute | The router waits once if the wait is 90 seconds or less |
| Thin source (one short release) | Short piece, and the Examiner will score Judgment and Evidence quality low. See open questions |

## Still open

| Question | Notes |
|---|---|
| Which free model writes best? | Bake-off in [BAKEOFF.md](BAKEOFF.md) |
| One press release is thin evidence for a 1,000-word deep dive | Needs the Researcher to pull in Acts, reports and earlier releases. Only PIB is readable today |
| Recall questions can be wrong | The Fact-checker checks them against claims. Not yet audited by a person |
