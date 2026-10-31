# Pipeline design

Status: draft 0.1, written 31 October 2026. Prices come from Anthropic's published list as cached on 6 October 2026. Token counts are assumptions to be replaced by measurements from the first run.

## What this is for

The pipeline turns the day's official documents into published editorials with no human in the loop. This note decides its shape: how many steps, which steps use a model, which model, who checks whom, what stops a bad piece going live, and what it costs.

## Terms used here

| Term | Meaning |
|---|---|
| Stage | One step of the pipeline: Scout, Triage, Researcher, Writer, Fact-checker, Examiner |
| Issue | One topic that gets one editorial, built from one or more items |
| Evidence pack | The documents and passages the Researcher hands to the Writer |
| Claim | Any fact, figure, date or attribution in an editorial |
| Revision loop | A draft that fails a check goes back to the Writer with the failures listed |
| Publish gate | Fixed rules, in code, that decide whether a draft goes live. See the [product definition](../PRODUCT.md) |
| Effort | A setting on the model that trades thinking time and cost against quality |
| Agent loop | A model that chooses its own next action (search, read, search again) until it decides it is done |

## The key idea

**A fixed line of stages, run by plain code, with one small agent inside it.**

The order of stages never changes, and code (not a model) decides when a draft is retried, held or published. The one place a model chooses its own actions is the Researcher, because only it cannot know in advance which documents it will need. Everything else is a single, bounded call.

This answers the question "is it agentic?": yes, where it pays (research), and no where predictability matters more (selection, writing, checking, publishing).

## The stages

| Stage | Job | Model | Why this model | Checked by |
|---|---|---|---|---|
| Scout | Fetch the day's items, drop duplicates | None (plain code) | Fetching and hashing need no model | Source run records (see [storage design](../knowledge-base/STORAGE_AND_RETRIEVAL.md)) |
| Triage | Score exam relevance, tag a syllabus topic, link past questions | `claude-haiku-5-5` | Many short items, a simple judgement, cheapest model. Run through the batch interface at half price | A labelled sample, measured against the back-test |
| Researcher | Gather the evidence pack for each chosen issue | `claude-sonnet-5-5`, as a bounded agent loop | Needs to pick tools and read long documents, but not to write well | Writer and Fact-checker both |
| Writer | Write the claims, then the three reading depths, the Mains question and the recall questions | `claude-opus-5-5` | The writing is the product, so this is where the strongest affordable model goes | Fact-checker, Examiner |
| Fact-checker | Check every claim against the passage it cites | `claude-sonnet-5-5`, in a fresh context, plus a code check | A different model and a different context from the Writer. Sees only the claim and its passage, never the Writer's reasoning | The code check (below) |
| Examiner | Score the draft against the [rubric](../QUALITY_RUBRIC.md) | `claude-sonnet-5-5`, in a fresh context | Same independence reason. Scoring is cheaper than writing | Blind human review during evaluation |
| Publish gate | Decide: publish, revise or hold | None (plain code) | A rule, not a judgement | Unit tests |

### Two checks that do not rely on a model

| Check | What it does |
|---|---|
| Quote check | Each claim must carry an exact quote from its source. Code confirms the quote appears in the stored passage, character for character. A claim whose quote is not found fails, whatever the Fact-checker said |
| Link check | Each claim must point to an item that exists in the database, from an allowed source |

These two catch invented sources and invented quotes, which are the worst failures, and they cost nothing.

### The publish gate

A draft goes live only if all of these hold:

| Rule | Source |
|---|---|
| Every claim passes the quote check and the link check | Code |
| Fact-checker marks no claim as unsupported or contradicted | Model |
| Rubric total is at least 70, and Accuracy is above 2 | [Rubric](../QUALITY_RUBRIC.md) |
| Topic is not on the sensitive list | Config file |
| Cost of this piece is under the cap | Cost counter |
| Kill switch is off | Config flag |

Otherwise: if the fault is fixable and this is the first or second attempt, the draft returns to the Writer with the failure list. After two failed attempts it is held and the maintainer is alerted. A held piece is never published and never silently dropped.

## Example run

| Step | What happens |
|---|---|
| 1 | At 06:00 the scheduler starts a run. Scout fetches 150 items from the source list, records one `source_run` per source, and drops duplicates |
| 2 | Triage scores the 140 new items in one batch. It keeps 12 and groups them into 8 issues |
| 3 | For the issue "draft rule on village councils", the Researcher searches the database, fetches the draft rule and the Act it comes under, and returns an evidence pack with exact passages |
| 4 | The Writer produces 14 claims, each with an exact quote and a source, then the three depths and the questions |
| 5 | The code checks run. One quote is not found in its passage. The draft fails and returns to the Writer with that failure |
| 6 | The revised draft passes the code checks. The Fact-checker finds no unsupported claims. The Examiner scores 78 with Accuracy 4 |
| 7 | The gate passes. The editorial publishes. Cost: about $1.80, since the Writer, Fact-checker and Examiner ran twice |
| 8 | A daily job picks 3 published pieces at random and runs the claim audit on them |

## Choices considered

### Overall shape

| Option | What it is | For | Against | Verdict |
|---|---|---|---|---|
| A. Fixed stages in code, one bounded agent for research | Described above | Predictable cost and behaviour. Each stage can be tested and swapped alone. Failures are located | More code than a single prompt. Stage hand-offs must be defined | **Chosen** |
| B. One free-roaming agent with all the tools | A single model decides what to do next, end to end | Least code. Flexible | Cost and path vary run to run. A failure is hard to locate. The model grades its own work. No clean place for the gate | Ruled out |
| C. One large prompt | All sources in, editorial out | Simplest. Cheapest to build | Cannot check itself. A claim cannot be tied to a quote. Context bloats on heavy days | Ruled out |
| D. Anthropic-hosted agent service (Managed Agents) | Anthropic runs the loop and a sandbox | No loop code to write | We need our own cost cap, database, gate and retry rules in the loop. Less control for a small gain | Ruled out for now |

### Who checks the Writer

| Option | For | Against | Verdict |
|---|---|---|---|
| Same model, same context | Cheap | Shares its own blind spots and can talk itself into agreeing | Ruled out |
| Different model, fresh context, plus code checks | Independent. The code checks cannot be argued with | Extra calls | **Chosen** |
| Human editor | Highest assurance | Removed from v1 by decision. Replaced by the daily sampled audit | Not used |

### How the Writer returns its output

| Option | For | Against | Verdict |
|---|---|---|---|
| Free text, parsed afterwards | Easy to prompt | Parsing breaks. A claim and its quote can drift apart | Ruled out |
| Structured output with a fixed schema (claims, quotes, depths, questions) | The quote check can run on the data. Depths are built from the same claims, so figures cannot differ between them | Schema must be designed | **Chosen** |

## Cost per editorial

These are estimates. Prices are per million tokens: Haiku 5.5 $0.10 in, $0.50 out; Sonnet 5.5 $2 in, $10 out; Opus 5.5 $4 in, $20 out.

| Stage | Assumed tokens (in / out) | Cost |
|---|---|---|
| Triage (share of one issue) | 12k / 1k, batch half price | about $0.00 |
| Researcher | 80k / 4k, including several reads | $0.20 |
| Writer, first pass | 40k / 25k, including thinking | $0.66 |
| Fact-checker | 30k / 4k | $0.10 |
| Examiner | 15k / 2k | $0.05 |
| **Happy path** | | **about $1.00** |
| With two revisions | Writer, Fact-checker and Examiner run three times | about $3.00 |

At 8 issues a day: roughly $8 a day on a clean run, up to about $24 on a bad day, so $240 to $720 a month. Caching the shared prompt and evidence pack, and setting effort lower on the Researcher, Fact-checker and Examiner, should cut this. Measure first.

**Cost limits in code:** a per-piece cap (default $4) and a per-day cap (default $40). When a cap is hit, the piece is held, not cut short. The cost counter reads the `usage` field of every response.

## Rules that follow from the engineering checklist

| Rule | Why |
|---|---|
| Retry only on 429, 5xx and network errors. Never retry other 4xx. Use the SDK's built-in retry and no second layer on top | A 4xx will not succeed on retry. Stacked retries multiply calls during an outage |
| A response that stops with `refusal` is not retried with the same prompt. The piece is held and logged. The server-side refusal fallback is on for the Writer | A refusal repeated is a refusal wasted |
| Each stage writes its result to the database before the next starts. A rerun resumes from the last finished stage | A crash must not repeat paid work |
| A run that does nothing is an error, not "done". A run with zero items from every source raises an alert | An outage must never look like a quiet news day |
| Long reads and embeddings run off the main loop and in batches | Keeps the process responsive |
| No forced tool choice. Output shape comes from structured outputs | Current models reject forced tool choice |
| Count model calls per issue at normal load and when failing. Target at most 6 calls on the happy path and at most 14 with two revisions | Keeps the cost bound visible |

## What can go wrong

| Risk | Response |
|---|---|
| The Writer invents a quote or a source | The quote check and link check fail it in code |
| The Fact-checker misses a wrong claim | Daily sampled audit. A rising error rate pauses publishing |
| Examiner scores too kindly | Compare Examiner scores with blind human scores in the evaluation phase, and tune the prompt until they agree |
| The Researcher loops or wanders | Hard limit on steps and on tokens per issue. It returns what it has, marked incomplete, and the gate holds the piece |
| A source returns 403 or changes layout | The source run is marked failed and an alert is sent. Other sources continue |
| One bad item breaks the run | Each issue runs on its own. One failure holds one issue, not the day |
| Prices or models change | Model names and caps are in one config file. The benchmark can be re-run on a new model before switching |
| Cost spikes | Per-piece and per-day caps, and the kill switch |

## What is still open

| Question | Notes |
|---|---|
| Is Opus the right Writer, or does Sonnet match it on the benchmark? | Test both on three benchmark topics before D4.5 is locked. If Sonnet matches, cost drops by about half |
| Which embedding model, and what size? | Needed by the [storage design](../knowledge-base/STORAGE_AND_RETRIEVAL.md) |
| What goes on the sensitive-topic list? | Needed for the gate. Start with courts, communal issues, elections, religion |
| How long can a run take? | The scheduler's time limit decides how many issues run in parallel |
| Where does the pipeline run? | A scheduler on a free tier is the plan. Confirm in the app stack decision |
| Who is alerted when a piece is held, and how? | The maintainer. Channel not chosen |
