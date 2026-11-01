# Researcher

Status: built and run on real PIB items, 1 November 2026. Code: `steelframe/pipeline/researcher.py` and `documents.py`.

## What this is for

Triage says which items matter. The Researcher collects the **exact text** the Writer may rely on. It returns an **evidence pack**: a short list of passages, each copied word for word from a stored page. The Writer may only quote from the pack, and code later checks every quote against it.

## Terms

| Term | Meaning |
|---|---|
| Issue | One kept item that will get one editorial |
| Passage | About 1,500 characters of a release, stored with an id such as P11 |
| Evidence pack | The passages chosen for one issue, plus gaps and problems |
| Link-only source | A source whose terms forbid keeping a copy (RBI). Its items can be linked but never quoted |
| Step | One model decision: search, fetch or done |

## How it works

| Step | Who | What happens |
|---|---|---|
| 1 | Code | Pick up to 3 kept items: highest relevance first, one per topic, skipping link-only sources and items that already have a pack |
| 2 | Code | Fetch the main item's page, cut it into passages, store them |
| 3 | Model | Sees the passages. Chooses `search` (stored titles and passages, full-text), `fetch` (another stored item), or `done` with the passage ids it wants |
| 4 | Code | Runs the action. The model never touches the network or the database |
| 5 | Code | After at most 6 steps, builds the pack from the stored text of the chosen ids |
| 6 | Code | Marks the pack **complete** only if the model finished, the main item is in the pack, and every chosen id was real |

The pack is saved in the `evidence_pack` table. A rerun skips items that already have one.

## Example

| Step | What happens |
|---|---|
| 1 | Item 38: "Union Government releases tax devolution of ₹1,09,019 crore". Code fetches the page and stores passage P11 |
| 2 | The model reads P11, decides it is enough, and answers `done` with `["P11"]` |
| 3 | The pack holds P11 word for word, with the page address and fetch time. Complete, 2 model calls in total |

Real run on 1 November 2026: 3 of 3 packs complete, 1 to 2 model steps each.

## Why code, not the model, does the first fetch

In a first version the model chose the first action. Free models sometimes repeated the same fetch or never finished, so a pack came back empty. The main item is always needed, so code reads it and the model starts with the text in front of it.

## Choices considered

| Option | For | Against | Verdict |
|---|---|---|---|
| A. Model picks JSON actions, code runs them | Works on every free model. No tool-calling API needed. Easy to bound and test | A model can return bad JSON, so each answer is checked and the router moves on | **Chosen** |
| B. Provider tool-calling APIs | Cleaner on paper | Support differs across the free providers, and forced tool choice is rejected by current models | Ruled out |
| C. No agent: always fetch the item and the top 3 search hits | Cheapest, fully predictable | Cannot follow a reference to an earlier release, which is the point of a Researcher | Ruled out |
| D. Keep whole pages as the evidence | Nothing is missed | Long prompts, and the quote check needs short passages to be useful | Ruled out |

## What can go wrong

| Risk | Response |
|---|---|
| The model names a passage it never saw | The id is dropped, noted in `problems`, and the pack is marked incomplete |
| The model never finishes | Hard limit of 6 steps. The pack is marked incomplete and the gate will hold it |
| A page is blocked or empty | The reason is recorded in `problems`. Other issues continue |
| Every model is down | That issue fails loudly (exit code 2 if all fail) and is retried next run |
| RBI item chosen | Never selected. RBI terms forbid keeping a copy |
| A table-only page | Table rows are read as text. A page that is only an image or PDF gives no text and is reported |

## Still open

| Question | Notes |
|---|---|
| Only PIB is readable | RBI needs written permission. PRS, the Gazette and court judgments have no feed yet |
| Search is words only, no embeddings | The embedding model is an open question in the storage design. Full-text search is enough for a small store |
| History is thin | The store holds only days of items so far, so "earlier releases" are few. It improves as Scout runs daily |
| Grouping several items into one issue | Not done. One item is one issue |
| PDF attachments | Not read |
