# Product Definition

Status: draft 0.1. Decisions here are settled for the first version. Open questions are listed at the end.

## In one paragraph

Steelframe is a free, open-source website that gives people preparing for the UPSC Civil Services Examination a daily set of current affairs editorials. Each editorial explains one issue, ties it to the exam syllabus, shows where every claim comes from, and ends with a few questions to help the reader remember it. It is written by an automated pipeline, checked by a second automated pass, and approved by a human editor before it is published.

## Terms used here

| Term | Meaning |
|---|---|
| UPSC | The Union Public Service Commission, which runs the exam |
| Civil Services Examination | The exam that selects officers for the Indian Administrative Service and other services |
| Aspirant | A person preparing for the exam |
| Prelims | The first stage: objective questions |
| Mains | The second stage: written, long-form answers |
| GS | General Studies: four Mains papers on history and society, governance and international relations, economy and environment, and ethics |
| Current affairs | Recent events and policy that the exam draws on |
| Editorial | In this document, one Steelframe piece on one issue |
| Claim | Any fact, figure, date or attribution stated in an editorial |
| Primary source | The original document behind a claim: a law, a court judgment, a government report, a press release |
| Syllabus | The official list of topics the exam can cover |
| PYQ | Previous year question |
| Pipeline | The chain of automated steps that produces an editorial |
| Human editor | A person who reads and approves an editorial before it is published |

## The problem

An aspirant has to follow a year of news and decide, every day, what matters for the exam and how it links to the syllabus. Two kinds of help exist today.

| Kind | Strength | Weakness |
|---|---|---|
| News sites and apps | Fast and wide | Leave the aspirant to decide what matters for the exam |
| Coaching editorials | Exam-shaped and structured | Written by hand, on a fixed schedule, mostly behind a paywall, and claims rarely show their sources |

A review of three established coaching products found the same gaps in all of them:

- A reader cannot check a claim from the page.
- Points are listed with equal weight, with little judgment on which matter or whether a measure will work.
- Each product offers one fixed length.
- Reading does not turn into remembering.
- Errors can reach readers, and corrections are not visible.

Steelframe aims to close these gaps, not to copy the products.

## Who it is for

| Group | Included in the first version |
|---|---|
| Aspirants preparing for the exam, first attempt or repeat | Yes |
| Language | English only |
| Working professionals studying part time | Yes, through short readable versions |
| Optional-subject, essay and interview preparation | No |

## What the first version includes

| Included | Notes |
|---|---|
| Daily editorials on GS current affairs | The core product |
| Syllabus and past-question links on every editorial | Each point is tied to its topic and the questions it answers |
| A source on every claim | Tap a figure, see the document and the passage |
| Three reading depths | A short brief, the full editorial, and a deep dive |
| Recall questions | Three per editorial, with a revision queue for the ones you miss |
| A syllabus map | Shows what has been in the news, by topic |
| Saved items, highlights and notes | Kept in the reader's account |
| Streaks | A quiet record of the days you read |
| Preferences | Default reading depth and topics you follow |
| A website only | No app, no offline mode |

## What it does not include

| Not included | Why |
|---|---|
| Feedback on Mains answers | High value, but hard to get right. Bad feedback would hurt trust more than none |
| Hindi and other languages | Doubles the work of checking facts. Revisit once quality is proven |
| Optional subjects, essay, interview | Widens the work for little added pull |
| Test series, notes, courses | A different product |
| Payments and pricing | Free in the first version. Pricing is decided later |
| Syncing between devices | Web only. An account still keeps saves in any browser |
| A "percent of syllabus covered" tracker | Current affairs has no fixed syllabus to finish, so the number would mislead |

## How a day works: an example run

The example is illustrative. The issue, numbers and steps are made up to show the flow.

| Step | What happens |
|---|---|
| 1. Collect | In the morning, the system gathers new items from official sources and news outlets: ministry releases, committee reports, court orders, newspapers. It removes duplicates. |
| 2. Choose | Each item is scored for exam relevance and linked to a syllabus topic and past questions. Say a ministry has published a draft rule. It scores high. A routine appointment scores low and is dropped. |
| 3. Research | For the draft rule, the system fetches the draft itself, the law it comes under, and earlier background. These are the primary sources. |
| 4. Write | A draft editorial is produced: what changed, the background, the main arguments for and against, a view on whether it will work, the way forward, and a Mains angle. It also produces three recall questions. |
| 5. Check claims | A second, separate pass checks every claim in the draft against its source. Say it finds that one figure in the draft does not match the document. It sends the draft back with that note. |
| 6. Score | The corrected draft is scored against the [quality rubric](QUALITY_RUBRIC.md). Say it scores 78. It passes the minimum of 70 and has no accuracy failure. |
| 7. Human approval | A human editor reads the editorial, looks at any flagged claims, and approves it. |
| 8. Publish | The editorial appears on the Today page in three depths. Every claim links to its source. |
| 9. Read | In the evening, an aspirant opens it. They read the brief, then the editorial. They tap a figure and see the passage. They highlight a paragraph and answer the three questions. One answer is wrong, so that question returns in the revision queue in a few days. |

If step 5 or step 6 fails twice, the draft is not published that day. A human decides what to do.

## Principles that shape the first version

| Principle | Effect |
|---|---|
| Evaluation before features | The app is not built until the writing beats a defined benchmark in blind review |
| Every claim has a source | A claim that cannot be traced does not ship |
| Exam-shaped, not news-shaped | Content is chosen and framed by the syllabus and past papers |
| Humans stay accountable | A human editor approves every piece until error rates justify less review |
| Respect the sources | We link to and summarise sources within their terms, with no wholesale copying |
| Open | The code and the rubric are public under the Apache License 2.0 |
