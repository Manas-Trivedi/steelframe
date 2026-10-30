# Past Paper Tagging

Status: pilot. Two Prelims papers and four Mains papers are tagged. The rest are not.

## What this is for

Tags say which syllabus topic each past question tests, and whether answering it needed recent news. They feed two things:

- **The back-test.** Using only news published before an exam date, would our coverage have matched what was asked?
- **Past-question links.** Each editorial can point to the past questions that its points answer.

## What a tag holds

| Field | Meaning |
|---|---|
| Year, stage, paper | Which paper the question came from |
| Question number | The number printed in the paper. For Mains, a question's position in the paper (see limits below) |
| Topic | One id from the [topic list](../../data/syllabus/gs_topics.yaml), the topic the question mainly tests |
| `ca` | `y` if answering needs recent news (roughly the last 18 months), `n` if it tests static knowledge |

Tags hold no question text. See the [reuse policy](PAST_PAPERS_POLICY.md). Files are in `data/past_papers/tags/`, one per paper, named `YEAR_STAGE_PAPER.tsv`.

## How tagging was done

1. The official papers were read locally and split into numbered questions (see `tools/past_papers/`).
2. Each question was assigned one topic and a `ca` flag, by Claude reading the question.
3. `tools/past_papers/summarise_tags.py` checks every topic id against the topic list and prints a summary.

No human has reviewed these tags yet. The `ca` flag is a judgment, and borderline cases can go either way.

## Pilot results

| Paper | Questions tagged | Needing recent news |
|---|---|---|
| Prelims GS-I, 2022 | 97 of 100 | 40 (41%) |
| Prelims GS-I, 2026 | 98 of 100 | 46 (46%) |
| Mains GS1, 2026 | 20 | 3 (15%) |
| Mains GS2, 2026 | 20 | 8 (40%) |
| Mains GS3, 2026 | 20 | 7 (35%) |
| Mains GS4, 2026 | 19 parts | 1 (5%) |

Where the 2026 Prelims paper's recent-news questions fall, by syllabus area: GS3 (technology, economy, environment, security) 33, GS2 (governance, international relations) 7, GS1 3, other 3. In 2022 the split was GS3 21, GS2 15, GS1 4.

## What this suggests, with caution

- In both Prelims papers, close to half the questions needed recent news. For 2026, almost three-quarters of those fell in the GS3 area, led by technology, space and defence, biodiversity and the economy.
- Mains questions lean less on news than Prelims, and GS4 hardly at all.
- This is two Prelims papers. Do not read trends into it. It shows what the tagging gives us, not a finding.

## Limits

- **Three questions in 2022 and two in 2026 are untagged.** The splitter did not find them, or merged them with a neighbour. The `completeness.csv` file lists the gaps.
- **Mains positions are approximate.** The printed question numbers are not in the OCR text, so Mains tags are keyed to a question's position, and for GS4 case studies to its parts. They are fit for the back-test. They are not yet exact enough to link a question to a specific past paper number, which needs a check against the official paper.
- **One tagger, no review.** Before the tags are used for anything that readers see, a person should check a sample and compare.
- **One topic per question.** Many questions test two. A second topic is not yet recorded.

## What is left

| Work | Needed |
|---|---|
| Tag the other years (Prelims 2014 to 2021 and 2023 to 2025, Mains 2014 to 2025) | Time and tagger. About 100 Prelims questions and 80 Mains questions per year |
| Fix Mains numbering against the official papers | A person with the papers open, or a better splitter |
| Review a sample of tags | A person who knows the syllabus |
| 2013 papers | Not available on the UPSC site. Needs another route |
