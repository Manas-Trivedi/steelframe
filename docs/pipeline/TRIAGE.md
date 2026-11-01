# Triage

Status: built and checked on 1 November 2026. Code: `steelframe/pipeline/triage.py`. Check: `steelframe/pipeline/triage_eval.py`.

## What this is for

Scout collects 100 to 300 items a day. Most are ceremonies, auctions and greetings. Triage reads only the **title** of each new item and decides which few are worth an editorial. It also tags each one with a syllabus topic, so the later stages can find the past questions that touch it.

## Terms

| Term | Meaning |
|---|---|
| Relevance | A score from 0 to 3 for how useful the item is to a General Studies answer |
| Kept | An item with relevance 2 or 3. Only kept items go on to the Researcher |
| Topic | One id from the 65-topic list in `data/syllabus/gs_topics.yaml`. `X.OTHER` means nothing fits |
| ca | "y" if a question on this needs recent news, "n" if it is static knowledge |

## How it works

| Step | What happens |
|---|---|
| 1 | Pick items with no triage row yet, newest first, up to 200 per run |
| 2 | Send 25 titles per call, with the topic list. Free model, route `triage` in `config/models.json` |
| 3 | Code checks the answer: one entry per title, relevance 0 to 3, a real topic id, ca is y or n. A bad answer is rejected and the router tries the next model |
| 4 | A batch is saved all at once. If every model fails, that batch stays untriaged and is retried next run |
| 5 | Kept items are listed with their topic and how many past questions sit under it (`kept_with_links`) |

| Relevance | Meaning | Example |
|---|---|---|
| 0 | No exam use | A speech text, a pledge, an auction result |
| 1 | Marginal | A deadline extension, a workshop |
| 2 | Useful | A data release, a ministry decision |
| 3 | High | A law, rule, court order, treaty or major economic decision |

## The check

30 real items (10 RBI, 20 PIB, fetched 1 November 2026) were labelled by hand in `data/triage/labels.csv`, then run through the real free models.

| Measure | Bar | Result |
|---|---|---|
| Keep or drop agrees with the label | at least 85% | 97% (29 of 30) |
| Labelled keeps the model dropped | 0 | 0 of 5 |
| Relevance within 1 of the label | none set | 100% |
| Exact relevance match | none set | 63% |
| Topic matches on the 5 keeps | none set | 100% |

The one disagreement: the model kept "Lending and Deposit Rates of Scheduled Commercial Banks" (label 1, model 2). A wasted keep costs one Researcher call. A missed keep is gone for good, so the bar is built to allow the first and forbid the second.

## Choices considered

| Option | For | Against | Verdict |
|---|---|---|---|
| A. Titles only, 25 per call | About 3,000 tokens per call. 200 items is 8 calls | A title can mislead | **Chosen** |
| B. Fetch each item's text and judge on it | More accurate | 200 fetches and a long prompt each. Several times the quota | Ruled out for now |
| C. Keyword rules | Free, no model | Misses new wording. Needs constant upkeep | Ruled out |
| D. One call per item | Simplest to validate | 200 calls a day, more than a free tier gives | Ruled out |

## What can go wrong

| Risk | Response |
|---|---|
| The model drops something important | Bar of zero missed keeps in the check. Daily audit of dropped items is open (below) |
| A model returns bad JSON or a made-up topic | Code rejects it and the next route is tried |
| Every model is down | The batch stays untriaged and the run exits non-zero |
| Hindi titles | Scout reads the English feed only, so none arrive |

## Still open

| Question | Notes |
|---|---|
| The check has 30 items, not the 40 planned | Only 30 English items existed. Re-run with more once Scout has collected them |
| Labels were written by the assistant, not an aspirant or teacher | Have a teacher relabel before trusting the 97% |
| Grouping kept items into issues | Done at Researcher time, not here |
