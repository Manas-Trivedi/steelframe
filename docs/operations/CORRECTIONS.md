# Corrections, audits and the alarm

Status: built 1 November 2026. Code: `steelframe/ops/`. Workflow: `.github/workflows/daily.yml` (written, **never run**).

## What this is for

No person approves each piece, so what happens after publishing matters. This note covers how an error is fixed in the open, how published pieces are re-checked every day, and what stops publishing when errors appear.

## Terms

| Term | Meaning |
|---|---|
| Correction | A dated note on a piece saying what was wrong and what is right |
| Takedown | A piece removed from the site, with a dated note saying why |
| Audit | A re-check of a random sample of published pieces |
| Alarm | A rule that pauses publishing when the audits show too many errors |
| Pause | A stored flag. While it is on, the daily run writes and publishes nothing |

## Corrections

| Step | What happens |
|---|---|
| 1 | A reader presses "Report an error" in the margin. It opens a prefilled form on the project's issue tracker |
| 2 | The maintainer checks the claim against its source |
| 3 | If it is wrong: `python3 -m steelframe.ops.corrections add ITEM_ID "what was wrong and what is right"` |
| 4 | The next site build shows the note, dated, at the top of the piece and on the Corrections page |
| 5 | If the piece cannot be saved: `... unpublish ITEM_ID "reason"`. It leaves the site and the Corrections page says it was taken down |

Nothing is changed silently. The piece text itself is not rewritten, because the note is the record.

## The daily audit

| Rule | Value |
|---|---|
| Sample | 3 published pieces a day, chosen at random |
| Code checks | Run again against the stored passages |
| Model check | A provider that neither wrote the piece nor checked it, when one is free. If none is, any provider except the Writer's |
| What it records | Claims checked, not fully supported, contradicted, the failures, the auditor model |

**This is an automated audit, not a human one.** The [accuracy audit](../evals/ACCURACY_AUDIT.md) asks for people who did not write the piece. This job only catches drift and gross errors. A human audit during the beta is still needed.

## The alarm

Publishing pauses when, over the last 14 days of audits:

| Condition | Why this line |
|---|---|
| Any claim is contradicted | That is a major error in the audit document's terms |
| More than 5% of audited claims are not fully supported | The audit document puts Accuracy 2 (a fail) above 5% |

While paused, `python3 -m steelframe.pipeline.daily` prints `PAUSED by the audit alarm`, exits 1, and changes nothing. After a person has looked and corrected or taken down the piece, `python3 -m steelframe.ops.audit resume` clears it.

## The scheduled job

`.github/workflows/daily.yml` runs at 06:00 India time. It restores the database, runs the tests, runs the pipeline, runs the audit, builds the site, saves the database to a `state` branch (a new commit each day, so history stays) and deploys the pages.

| Safeguard | Detail |
|---|---|
| Off by default | It does nothing until the repository variable `PIPELINE_ENABLED` is `true` and the three API keys are set as secrets |
| One run at a time | A concurrency group stops two runs writing the same database |
| Needs attention | If the pipeline or audit exits non-zero, the job still saves and publishes what finished, then fails so GitHub notifies the maintainer |

**Never run.** It could not be tried here. Expect to fix small things on the first real run (permissions, Pages settings, the git version for orphan worktrees).

## What can go wrong

| Risk | Response |
|---|---|
| The audit model is as wrong as the checker | Same blind spots. The human audit in the beta is the real test |
| A false alarm pauses publishing | One command clears it. The alarm prints why |
| A real error slips past all checks and the sample | The reader report link is the last line. The sample is small, so the audit finds common errors, not rare ones |
| The alarm is ignored | The job fails every day until someone acts |

## Still open

| Question | Notes |
|---|---|
| Who is notified, and where | GitHub's failure email only, for now |
| Sampling method for a stated confidence | The audit document asks for an established method. A flat 3 a day does not give one |
| Retention review and the public-launch decision | Need beta data (see the roadmap, D7) |
