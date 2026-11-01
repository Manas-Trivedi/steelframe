# Publish gate and the daily run

Status: built and run end to end on real data, 1 November 2026. Code: `steelframe/pipeline/gate.py`, `daily.py`. Settings: `config/gate.json`.

## What this is for

No human approves each piece (decided 31 October). So one set of fixed rules, in code, decides whether a draft goes live, goes back for a rewrite, or is held. This note also describes the daily run that ties every stage together.

## Terms

| Term | Meaning |
|---|---|
| Attempt | One draft by the Writer. The first is attempt 1. Each rewrite is the next number |
| Publish | The editorial is marked `published` and can be shown to readers |
| Revise | The draft fails. It goes back to the Writer with the list of failures |
| Hold | The draft is kept but never published. An alert line is printed and the run exits non-zero |
| Kill switch | `kill_switch` in `config/gate.json`. When true, nothing is fetched, written or published |

## The rules

A draft is published only if all of these hold.

| Rule | Checked by |
|---|---|
| Quote, link and figure checks pass for every claim | Code ([CHECKS.md](CHECKS.md)) |
| The Fact-checker marks every claim and recall question "supported" | Model, on another provider |
| Rubric total is at least 70 and Accuracy is above 2 | Examiner scores, code adds up ([EXAMINER.md](EXAMINER.md)) |
| The topic is not on `sensitive_topics` | Config: courts and judiciary (G2.SEP, G2.EXEC), communalism and religion (G1.EMP), elections (G2.RPA) |
| The kill switch is off | Config |

If a draft fails and it is attempt 1 or 2, it is **revised**. A failure at attempt 3 (`max_attempts`) is **held**. A sensitive topic is held at once, before any model call.

## How a run goes

| Step | What happens | If it fails |
|---|---|---|
| 0 | Kill switch on? Print `PAUSED` and stop | |
| 1 | Scout fetches the feeds | A failing source never hides the others; exit code reflects it |
| 2 | Triage scores new titles | A failed batch is retried next run |
| 3 | Researcher builds evidence packs for as many issues as the day's cap leaves room for (`daily_issue_cap`, 3) | An incomplete pack is never written from |
| 4 | For each waiting pack: check the free quota has room. If not, **defer** the issue to tomorrow | Never rushed with fewer checks |
| 5 | Write, then code checks, then Fact-checker (skipped if a code check failed), then Examiner (skipped if the fact-check failed), then the gate | Revise or hold |
| 6 | Save the result. Print a summary with the number of model calls | |

Every step saves before the next starts. An outage in the middle leaves the draft and the review in the database, and the next run continues from the last saved attempt without paying for the same draft twice.

**Exit codes:** 0 nothing held or failed; 1 something was held, failed or deferred; 2 nothing published and something failed. A scheduler can alert on non-zero.

## Real run, 1 November 2026

| Issue | Attempts | Score | Result |
|---|---|---|---|
| BIMSTEC maritime exercise | 1 | 89 | published |
| Tax devolution | 1 | 88 | published |
| MoHUA clean Delhi workshop | 1 | 82 | published |

8 model calls in the run (the three drafts already existed from earlier tests, so only checks and scores were paid for). The design target is about 10 calls per issue on a clean run.

## Choices considered

| Option | For | Against | Verdict |
|---|---|---|---|
| A. Fixed rules in code, models only produce scores and verdicts | Predictable, testable. A model cannot talk its way past the gate | Rules need tuning by hand | **Chosen** |
| B. Ask a model "should this publish?" | Flexible | Marks its own homework. Not testable | Ruled out |
| C. Publish everything and audit after | Fast | One wrong fact is public before anyone sees it | Ruled out |
| D. Hold everything for a human | Safest | Removed from v1 by decision | Ruled out |

**Daily cost cap.** There is no money cost (free models only). The cap is on **issues** (3 a day) and on the free quotas, which the router counts itself. If quota is short, issues wait.

## What can go wrong

| Risk | Response |
|---|---|
| The gate is too lenient because the Examiner is generous | The Examiner is uncalibrated ([EXAMINER.md](EXAMINER.md)). The daily audit and the error-rate alarm ([CORRECTIONS.md](../operations/CORRECTIONS.md)) are the backstop |
| The sensitive list is wrong | It is one line of config. Start wide, narrow with evidence |
| Everything is held every day | The exit code and ALERT lines make it visible. Raise `max_attempts` or fix the cause |
| Two runs at once | Not guarded. Run one scheduler. Open |

## Still open

| Question | Notes |
|---|---|
| Who gets the alert, and how? | Today: ALERT lines and a non-zero exit. Channel not chosen |
| Where does the run execute? | A scheduler on a free tier. Part of the stack decision |
