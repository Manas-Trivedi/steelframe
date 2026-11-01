# Writer bake-off

Status: run 1 November 2026. Code: `steelframe/pipeline/bakeoff.py`. **Inconclusive.** Three packs and one try each is too little to rank models. Read the numbers as "what goes wrong", not "who wins".

## What this is for

The Writer is the product. Which free model should write? This runs each candidate on the same three evidence packs and records whether its answer had the right shape, whether the quote, link and figure checks passed, and what the Examiner (on another provider) scored it.

## Terms

| Term | Meaning |
|---|---|
| Valid shape | The answer was JSON with all required parts, claims numbered in order, and passages that exist |
| Code checks pass | Every quote is in its passage, every source is allowed, every figure is in a claim |
| Pack | The evidence for one issue |

## How it ran

| Item | Value |
|---|---|
| Packs | 3 real PIB issues from 31 October 2026 (tax devolution, BIMSTEC exercise, MoHUA workshop) |
| Tries | 1 per model per pack. No revision loop |
| Scorer | The Examiner, on a provider other than the candidate's. Only drafts that passed the code checks were scored |
| Fact-check model | Not run, to save free quota |

## Result

| Model | Packs | Valid shape | Code checks pass | Mean score | Mean seconds |
|---|---|---|---|---|---|
| gemini/gemini-3.5-flash | 3 | 1 | 0 | n/a | 40 |
| gemini/gemini-3-flash-preview | 3 | 1 | 0 | n/a | 19 |
| gemini/gemini-3.1-flash-lite | 3 | 0 | 0 | n/a | 0 |
| groq/openai/gpt-oss-120b | 3 | 1 | 0 | n/a | 13 |
| groq/qwen/qwen3.8-27b | 3 | 1 | 0 | n/a | 46 |
| openrouter/nvidia/nemotron-3-ultra-550b-a55b:free | 3 | 1 | 0 | n/a | 497 |
| openrouter/google/gemma-4-31b-it:free | 3 | 0 | 0 | n/a | 65 |

No candidate passed the code checks on any pack in this run, so there are no scores to compare.

## What the failures were

| Failure | Seen with |
|---|---|
| Quote not in the passage word for word (often a table row paraphrased) | Gemini 3-flash-preview, gpt-oss-120b, qwen3.8-27b |
| A number in the text that no claim carries | Gemini 3.5-flash |
| Answer cut off or invalid JSON | Gemini 3.5-flash |
| Missing parts (no claims, too few brief bullets, too few sections) | Gemini 3-flash-preview, gpt-oss-120b, qwen3.8-27b |
| Rate limit or own quota ceiling reached | Gemini 3.1-flash-lite (no calls made: the daily ceiling was already used), gpt-oss-120b, qwen3.8-27b |
| Very slow (about 8 minutes a pack) | Nemotron Ultra |

## What else we know

| Fact | Source |
|---|---|
| In the earlier end-to-end run, Gemini 3.5-flash produced a draft that passed every check on the first try for 3 packs out of 3 (after one earlier attempt hit a cut-off) | [GATE.md](GATE.md) |
| The same model failed two of three packs in this bake-off | Above |

The same model passing and failing on the same packs shows how much one try varies. That variation is why the pipeline has a revision loop of up to 3 attempts that feeds the exact failures back.

## Decision

| Decision | Reason |
|---|---|
| Keep Gemini 3.5-flash first in the Writer route | Best observed result, and the fastest of the longer-answer models |
| Keep the fallbacks: Gemini 3-flash-preview, Nemotron Ultra, gpt-oss-120b | Different providers, so one outage or rate limit does not stop the Writer |
| Do not rank the others | The sample cannot support it |

## Choices considered

| Option | For | Against | Verdict |
|---|---|---|---|
| A. Rank by one try on three packs | Cheap | Noise swamps the signal | Not trusted |
| B. Repeat each model 5 times on 10 packs | A real answer | About 350 calls, more than a day of free quota for some providers | Do over several days, a few runs a day |
| C. Pick by the pipeline's own pass rate over the first weeks | Uses real runs, no extra calls | Slow to learn | **Chosen as the follow-up**: the `review` table records attempts and the writer model for every piece |

## Still open

| Question | Notes |
|---|---|
| Which model writes best? | Not known. Needs repeated runs, and human scoring of the output |
| Why quotes fail on table rows | Table rows are flattened to text ("4 BIHAR 10845"). A prompt hint or a table-aware passage format might help |
| Whether a smaller output (fewer deep-dive words) raises the pass rate | Untested |
