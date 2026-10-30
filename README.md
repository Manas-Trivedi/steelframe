<div align="center">

# Steelframe

**Current affairs for the civil services exam, written to the standard of the best coaching editorials.**

![status](https://img.shields.io/badge/status-pre--alpha-orange)
![stage](https://img.shields.io/badge/stage-evaluation%20first-blue)

[Overview](#overview) · [Principles](#principles) · [How it works](#how-it-works) · [Roadmap](#roadmap) · [Contributing](#contributing)

</div>

---

## Overview

Steelframe is an agentic system for UPSC Civil Services preparation. Every day it reads the primary sources, decides what matters for the exam, and produces a structured editorial: the issue explained, linked to the syllabus, with a Mains question and Prelims practice attached.

The name comes from the phrase "the steel frame of India", long used for the civil service itself.

Most current affairs products fall into two groups. News scrapers collect headlines and leave the aspirant to work out what is exam-relevant. Coaching editorials do that work well, but they are written by hand, on a fixed schedule, behind a paywall. Steelframe aims to match the quality of the second group with the coverage and speed of the first.

> **Status: pre-alpha.** Nothing here is production-ready. The repository currently holds the project definition and, shortly, the evaluation harness. See the [roadmap](#roadmap).

## Principles

| Principle | What it means in practice |
|---|---|
| **Evaluation before features** | We do not build the app until the writing beats a defined benchmark, judged blind by serious aspirants and teachers against the [quality rubric](docs/QUALITY_RUBRIC.md). |
| **Every claim has a source** | A claim that cannot be traced to a primary document does not ship. |
| **Exam-shaped, not news-shaped** | Content is selected and framed by the syllabus and past papers, not by what trended. |
| **Humans stay accountable** | A human editor signs off on output until measured error rates justify less review. |
| **Respect the sources** | We link to and summarise sources within what their terms allow. No wholesale copying. |

## How it works

The planned pipeline is a fixed sequence of specialised stages. The exact design is the subject of an upcoming design document, so treat this as the intended shape rather than a finished spec.

```
 Sources           Scout        Triage        Researcher      Writer
 PIB, PRS,   -->   ingest  -->  exam     -->  primary    -->  editorial,
 RBI, courts,      and          relevance,    documents,      Mains question,
 newspapers        dedupe       syllabus      history,        Prelims MCQs
                                links         data
                                                                  |
                         Published  <--  Examiner  <--  Fact-checker
                                         scores vs.     checks each claim
                                         the rubric     against its source
                                         (sends weak
                                          drafts back)
```

| Stage | Responsibility |
|---|---|
| Scout | Collect and deduplicate the day's source material. |
| Triage | Score exam relevance and link items to the syllabus and past questions. |
| Researcher | Pull in primary documents, background and data. |
| Writer | Produce the editorial in the agreed format. |
| Fact-checker | An independent pass that verifies each claim against its cited source. |
| Examiner | Score the draft against the [quality rubric](docs/QUALITY_RUBRIC.md) and return weak drafts for revision. |

## Roadmap

Work proceeds in order. Each phase must be reviewed before the next starts.

| Phase | Focus |
|---|---|
| Foundations | Repository, naming, working agreements. |
| Product definition | Competitor teardown, target user, quality rubric. |
| Evaluation | Past-paper back-testing, benchmark set, blind review. |
| Knowledge base | Source catalogue, syllabus map, past-question links. |
| Agent pipeline | The stages above, iterated until the benchmark is met. |
| Design | Reading experience and visual language. |
| App | Reader, syllabus navigation, revision, accounts. |
| Launch | Closed beta, correction process, public release decision. |

## Repository layout

The repository is at its starting point. Directories are added as each phase begins.

```
steelframe/
  docs/
    QUALITY_RUBRIC.md
  LICENSE
  README.md
```

## Contributing

The project is not yet open for code contributions while the foundations are settled. If you are an aspirant, mentor or educator and would like to help with benchmark reviews, open an issue describing your background and availability.

## License

Licensed under the [Apache License 2.0](LICENSE).
