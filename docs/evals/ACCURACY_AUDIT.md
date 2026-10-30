# Accuracy Audit

Status: draft 0.1. No audit has been run.

## What it is

An accuracy audit checks every claim in an editorial against the document it says it comes from. It produces the Accuracy score in the [quality rubric](../QUALITY_RUBRIC.md). It is the check that matters most, because one wrong fact costs more trust than anything else.

A review of existing coaching material found errors that a reader cannot catch from the page: a figure too large to be possible, and two different values for the same measure in one issue. The audit is built to catch exactly these.

## Terms used here

| Term | Meaning |
|---|---|
| Claim | One fact, figure, date, name or attribution stated in a piece |
| Source | The document the piece cites for a claim: a law, a judgment, a government report, a press release |
| Auditor | A person who checks claims. Not the person or system that wrote the piece |
| Verdict | The auditor's finding for one claim |

## What counts as a claim

| Counts | Does not count |
|---|---|
| A number, date, name or place stated as fact | A heading or a transition |
| "The Act requires X" or "the report found Y" | A clearly marked opinion, such as "this is likely to be too weak" |
| A comparison with a figure ("twice the earlier rate") | A definition of a general term that is not tied to a source |

Opinions are not audited for truth, but they are checked for being labelled as opinion and for citing the facts they rest on.

## Steps

1. **List the claims.** Extract every claim from the piece into the [audit sheet](forms/claim_audit_template.csv), one row each, with the source the piece cites.
2. **Find the source.** Open the cited source. Record whether it was found, and the page or section.
3. **Compare.** Read the source and decide a verdict.
4. **Rate severity.** For anything not fully supported, mark how serious it is.
5. **Second check.** A second auditor repeats steps 2 to 4 on a random 10% of claims. Disagreements are settled by a third person.
6. **Consistency check.** Compare every figure with the same measure elsewhere in the piece and across the pieces published that day.
7. **Score.** Turn the results into the Accuracy score using the table below.

## Verdicts

| Verdict | Meaning |
|---|---|
| Supported | The source says what the piece says |
| Partly supported | The source supports part of it, or says it with a caveat the piece dropped |
| Unsupported | The source is silent on it |
| Contradicted | The source says something different |
| Source not found | The cited document cannot be found or opened |
| No source cited | The piece gave nothing to check |

## Severity

| Level | Meaning | Example |
|---|---|---|
| Major | Changes the meaning, or would mislead an answer | A wrong year for a law, a figure out by a factor of ten, a claim attributed to the wrong body |
| Minor | A slip that does not change the meaning | A rounded figure, a date one day off |

## Turning results into the Accuracy score

| Score | Condition |
|---|---|
| 5 | Every claim supported |
| 4 | No major errors. At most 2% of claims minor, partly supported or unsupported |
| 3 | No major errors. Between 2% and 5% of claims minor, partly supported or unsupported |
| 2 | One major error, or more than 5% of claims not fully supported |
| 1 | Two or more major errors |

Under the rubric, a score of 2 or below fails the piece, whatever its total. "Source not found" and "No source cited" count as not fully supported.

## How much to check

| Stage | Rule |
|---|---|
| The benchmark pieces | Check every claim in every Steelframe piece and every reference piece. The pieces are few, so a full check is affordable, and it gives a fair comparison |
| Daily production | Draw a random sample each week. With no errors found, a sample of 59 claims gives 95% confidence that the true error rate is under 5%, and about 299 gives under 1%. If any error is found, the sample must grow. These numbers come from informal calculators and should be replaced by an established sampling method before they are relied on |
| Anything flagged | Every claim a reviewer or reader flags is checked, whatever the sample says |

## Who audits

| Rule | Why |
|---|---|
| Auditors did not write or edit the piece | Writers miss their own errors |
| The automated claim check in the pipeline is not the audit | The audit tests the automated check. If both used the same method they would share the same blind spots |
| Auditors record what they could not check | An unchecked claim is not a supported one |

## Reporting

| Output | Content |
|---|---|
| Per piece | Claim count, verdict counts, major and minor errors, the Accuracy score |
| Per run | Error rate with a confidence interval, error types, and which pipeline stage let each error through |
| Errors found | Each error is logged, fixed in the piece if it is live, and corrected visibly with the date |

## What can go wrong

| Risk | Response |
|---|---|
| The source changed after the piece was written | Keep a dated copy of the cited passage where the source's terms allow it, and audit against that |
| The source is paywalled or taken down | Mark it "source not found", and look for another primary source. Do not guess |
| Auditors disagree | The second-check rule and a third person settle it. The disagreement rate is reported |
| Auditing is slow | Measure minutes per claim in the first run, then decide how to scale |
| Claims are mistaken for opinions | The auditor flags borderline cases, and a second person decides |

## What is still open

| Question | Notes |
|---|---|
| Who the first auditors are | An evaluation-phase task. They need to read legal and government documents comfortably |
| The thresholds in the score table | Proposals. Test them on the first pieces |
| The sampling method for production | Replace the quick figures with an established method |
| How long a claim check takes | Unknown until the first run |
