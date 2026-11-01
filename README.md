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

For what the first version includes and leaves out, see the [product definition](docs/PRODUCT.md).

The name comes from the phrase "the steel frame of India", long used for the civil service itself.

Most current affairs products fall into two groups. News scrapers collect headlines and leave the aspirant to work out what is exam-relevant. Coaching editorials do that work well, but they are written by hand, on a fixed schedule, behind a paywall. Steelframe aims to match the quality of the second group with the coverage and speed of the first.

> Steelframe is an independent project. It is not affiliated with, endorsed by, or connected to the Union Public Service Commission. "UPSC" appears here only to describe the exam.

> **Status: pre-alpha.** The pipeline and the site are built and run end to end on real press releases, but the writing has **not** yet been tested against coaching material by human reviewers, and the site has not been opened in a real browser. Nothing here is production-ready. See [what the benchmark run does and does not show](docs/pipeline/BENCHMARK_RUN.md).

## Principles

| Principle | What it means in practice |
|---|---|
| **Evaluation before features** | We do not build the app until the writing beats a defined benchmark, judged blind by serious aspirants and teachers against the [quality rubric](docs/QUALITY_RUBRIC.md). |
| **Every claim has a source** | A claim that cannot be traced to a primary document does not ship. |
| **Exam-shaped, not news-shaped** | Content is selected and framed by the syllabus and past papers, not by what trended. |
| **Checked by machines, audited by people** | A fixed publish gate decides what goes live. A daily sample of published pieces is audited, and a high error rate pauses publishing. |
| **Respect the sources** | We link to and summarise sources within what their terms allow. No wholesale copying. |

## How it works

The planned pipeline is a fixed sequence of specialised stages. The exact design is the subject of an upcoming design document, so treat this as the intended shape rather than a finished spec.

```
 Sources           Scout        Triage        Researcher      Writer
 PIB, PRS,   -->   ingest  -->  exam     -->  primary    -->  editorial,
 RBI, Parliament,  and          relevance,    documents,      Mains question,
 courts, data      dedupe       syllabus      history,        Prelims MCQs
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

## Try it

Python 3.9 or later. No packages to install. Node is only needed for the browser-script tests.

| Task | Command |
|---|---|
| Run all tests | `python3 -m unittest discover -s tests -t .` |
| Fetch the feeds | `python3 -m steelframe.scout.run` |
| Run the whole daily pipeline | `python3 -m steelframe.pipeline.daily` (needs free API keys in `.env`, see `.env.example`) |
| Audit published pieces | `python3 -m steelframe.ops.audit run` |
| Build the site | `python3 -m steelframe.site.build`, then open `site/dist/index.html` |

Only free models are used, and the router refuses anything else. A daily workflow exists in `.github/workflows/daily.yml`; it does nothing until switched on.

## Where to read next

| Topic | Document |
|---|---|
| The pipeline's shape | [PIPELINE_DESIGN.md](docs/pipeline/PIPELINE_DESIGN.md) |
| Each stage | [Triage](docs/pipeline/TRIAGE.md), [Researcher](docs/pipeline/RESEARCHER.md), [Writer](docs/pipeline/WRITER.md), [Checks](docs/pipeline/CHECKS.md), [Examiner](docs/pipeline/EXAMINER.md), [Gate and daily run](docs/pipeline/GATE.md) |
| Evidence the pipeline works | [Bake-off](docs/pipeline/BAKEOFF.md), [Benchmark run](docs/pipeline/BENCHMARK_RUN.md) |
| Design | [Direction](docs/design/DESIGN_DIRECTION.md), [Language](docs/design/DESIGN_LANGUAGE.md), [3D concepts](docs/design/3D_CONCEPTS.md) |
| The app | [Stack](docs/app/STACK.md), [Site](docs/app/SITE.md) |
| After publishing | [Corrections, audits and the alarm](docs/operations/CORRECTIONS.md) |

## Repository layout

```
steelframe/        Python package: llm/ (free-model router), scout/, pipeline/, ops/, site/
site/              Static assets (CSS tokens, styles, scripts) and site.json
config/            Feeds, model routes and quotas, publish-gate settings
data/              Syllabus topics, past-paper tags, benchmark list, Triage labels, source list
docs/              Product, rubric, evals, pipeline, design, app, operations
tests/             Python tests, and tests/js for the browser logic
tools/             One-off scripts (past papers, PIB probe)
.github/workflows/ The daily job (off by default)
```

## Contributing

The project is not yet open for code contributions while the foundations are settled. If you are an aspirant, mentor or educator and would like to help with benchmark reviews, open an issue describing your background and availability.

## License

Licensed under the [Apache License 2.0](LICENSE).
