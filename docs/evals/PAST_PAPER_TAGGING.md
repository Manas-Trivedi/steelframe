# Past Paper Tagging

Status: 12 of 13 Prelims GS-I papers (2014 to 2026) are tagged, except 2020 and 2024. Four Mains papers (2026) are tagged. Other Mains years are not.

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

## Results

| Paper | Questions tagged | Needing recent news |
|---|---|---|
| Prelims GS-I, 2014 | 91 of 100 | 20 (21%) |
| Prelims GS-I, 2015 | 89 of 100 | 27 (30%) |
| Prelims GS-I, 2016 | 86 of 100 | 47 (54%) |
| Prelims GS-I, 2017 | 100 of 100 | 41 (41%) |
| Prelims GS-I, 2018 | 100 of 100 | 43 (43%) |
| Prelims GS-I, 2019 | 96 of 100 | 42 (43%) |
| Prelims GS-I, 2021 | 100 of 100 | 35 (35%) |
| Prelims GS-I, 2022 | 97 of 100 | 40 (41%) |
| Prelims GS-I, 2023 | 98 of 100 | 56 (57%) |
| Prelims GS-I, 2025 | 96 of 100 | 52 (54%) |
| Prelims GS-I, 2026 | 98 of 100 | 46 (46%) |
| Mains GS1, 2026 | 20 | 3 (15%) |
| Mains GS2, 2026 | 20 | 8 (40%) |
| Mains GS3, 2026 | 20 | 7 (35%) |
| Mains GS4, 2026 | 19 parts | 1 (5%) |

Across the 11 tagged Prelims papers, 449 of 1,051 questions (43%) needed recent news. By syllabus area they fall: GS3 284, GS2 110, other 32, GS1 23. The most frequent topics are biodiversity and climate (54), the economy (43), IT, space and biotech (42), agriculture (31) and environment (31).

## What this suggests, with caution

- Across the tagged Prelims papers, about four in ten questions needed recent news. The share has risen over time, from about a quarter in 2014 and 2015 to over half in 2023 and 2025.
- About two-thirds of those questions sit in the GS3 area (environment, economy, science and technology, agriculture). Editorials should lean that way first.
- Mains questions lean less on news than Prelims, and GS4 hardly at all.
- One tagger, no review, so the rise over time could partly be the tagger being stricter on older papers. Treat it as a guide, not a finding.

## Limits

- **Some questions are untagged in every paper.** The splitter did not find them, or merged them with a neighbour. The `completeness.csv` file lists the gaps. Junk entries (exam instructions) were left out.
- **2020 and 2024 are not tagged.** The OCR text for these two repeats questions and gives some the wrong number, so tags keyed to the numbers would point at the wrong questions. They need a re-run of the OCR first.
- **Mains positions are approximate.** The printed question numbers are not in the OCR text, so Mains tags are keyed to a question's position, and for GS4 case studies to its parts. They are fit for the back-test. They are not yet exact enough to link a question to a specific past paper number, which needs a check against the official paper.
- **One tagger, no review.** Before the tags are used for anything that readers see, a person should check a sample and compare.
- **One topic per question.** Many questions test two. A second topic is not yet recorded.

## What is left

| Work | Needed |
|---|---|
| Re-OCR Prelims 2020 and 2024, then tag them | A cleaner reading of the two-column layout |
| Tag Mains 2014 to 2025 | Mains numbering is unreliable (see above), so this waits for a better splitter. About 80 questions per year |
| Fix Mains numbering against the official papers | A person with the papers open, or a better splitter |
| Review a sample of tags | A person who knows the syllabus |
| 2013 papers | Not available on the UPSC site. Needs another route |
