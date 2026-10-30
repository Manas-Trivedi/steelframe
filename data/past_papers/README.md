# Past paper index

A list of links to official UPSC Civil Services Examination question papers. It holds links only. See [the reuse policy](../../docs/evals/PAST_PAPERS_POLICY.md) for why no question text or PDF is stored in this repository.

## Files

| File | What it holds |
|---|---|
| `index.csv` | One row per paper: year, stage, paper, the official link, and where the link was found |
| `missing.csv` | Papers in scope that were not found on the UPSC website |

## Columns in `index.csv`

| Column | Meaning |
|---|---|
| `year` | Year of the examination |
| `stage` | `Prelims` or `Mains` |
| `paper` | `GS-I` (Prelims General Studies), `CSAT` (Prelims Paper II), `Essay`, or `GS1` to `GS4` (Mains General Studies papers I to IV) |
| `official_url` | Link to the PDF on upsc.gov.in |
| `source` | `listing` if found on the main or archive listing, `exam page` if found on that exam's own page |

## Scope

Prelims General Studies Paper I and Paper II (CSAT), and the Mains Essay and General Studies papers I to IV, for 2013 to 2026. Optional subjects, language papers and other exams are out of scope.

## Coverage

All years from 2014 to 2026 are indexed. **2013 is not available** on the UPSC website, in the listing, the archive, or per-year pages. These links were collected on 30 October 2026 and UPSC may move files, so the links can break.

## How it was built

1. Read the current listing and the archive listing at upsc.gov.in/examinations/previous-question-papers, which cover 2016 to 2026 apart from the 2017 Prelims.
2. Read the per-exam pages for the 2014, 2015 and 2017 gaps.
3. Kept only the in-scope papers and normalised their names.
4. Checked that each year has the expected papers. Content checks, to confirm that each file is the paper it claims to be, are a later step.
