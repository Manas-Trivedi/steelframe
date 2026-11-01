# Checks: quote, link, figure and the Fact-checker

Status: built and tested on real drafts, 1 November 2026. Code: `steelframe/pipeline/checks.py`, `fact_checker.py`.

## What this is for

The Writer is a free model and will sometimes get things wrong. These checks decide whether a draft's claims can be trusted. Three are plain code and cannot be argued with. One is a second model that did not write the draft.

## Terms

| Term | Meaning |
|---|---|
| Claim | One fact with an exact quote and a passage id |
| Passage | A stored piece of a source page |
| Verdict | The Fact-checker's judgement of one claim: supported, partly, unsupported or contradicted |

## The four checks

| Check | Who | Passes when | Catches |
|---|---|---|---|
| Quote | Code | Each claim's quote is in its passage, character for character. Only spacing, curly quotes and dashes are ignored. Case matters | Invented or altered quotes |
| Link | Code | Each claim's passage is in the evidence pack, and its source allows a copy | Invented sources, link-only sources |
| Figure | Code | Every number in the brief, editorial, deep dive, Mains question and approach, and the stems and explanations of the recall questions also appears in a claim. "Seven" in a claim covers "7" in the text. List numbers such as "1." are ignored. Answer options are not checked, because wrong options may hold any number | A figure that was not sourced, or that differs between depths |
| Fact-check | Model | Every claim, and the marked answer of every recall question, is "supported" by the passage | A claim that says more, less or something different from its quote |

**Order and cost.** The three code checks run first. If any fails, the model is not called, because the draft goes back to the Writer anyway. That saves one call.

**Independence.** The Fact-checker runs on a provider other than the one that wrote the draft (the router is told to skip it). It sees the passages, the claims and the recall questions. It never sees the Writer's reasoning or the long text.

**Strict on purpose.** "Partly" fails a draft. A claim that merges three facts but is backed by one is a wrong claim to a reader.

## Example

| Step | What happens |
|---|---|
| 1 | The Writer's draft says "Rs 1,09,019 crore" in the brief and "Rs 1,19,019 crore" in the editorial |
| 2 | The figure check finds 119019 in no claim: "editorial: the figure(s) 119019 appear in no claim" |
| 3 | The draft returns to the Writer with that line. No model call was spent on checking |

## Tested with planted errors

On a real draft (the 31 October tax devolution release), three claims were changed by hand while their quotes stayed the same. The Fact-checker caught all three, and the recall question that depended on one.

| Planted error | Verdict |
|---|---|
| Amount changed from Rs 1,09,019 crore to Rs 2,09,019 crore | contradicted |
| "in addition to" changed to "replaces" | contradicted |
| Purpose changed to repaying pandemic debts | unsupported |

## What can go wrong

| Risk | Response |
|---|---|
| The Fact-checker is too kind | Daily audit of published pieces. Compare with human audits during evaluation |
| The Fact-checker is too harsh and blocks good drafts | The failure notes go back to the Writer. Two tries, then hold |
| Every model is down | The stage raises, the draft stays unchecked, and nothing is published |
| A model is on the Writer's provider because the others are down | Allowed only if no other route exists; the gate records both models |
| The figure check rejects a legitimate static fact (such as an Article number) | Yes, deliberately. A figure must come from a passage, or it is left out |

## Still open

| Question | Notes |
|---|---|
| Static background (Articles, Acts, earlier years) is blocked by the figure check | Needs the static base (see `docs/knowledge-base/STATIC_BASE.md`) turned into stored passages the claims can cite |
| Both checkers are free models | Their agreement with a human auditor is unmeasured |
