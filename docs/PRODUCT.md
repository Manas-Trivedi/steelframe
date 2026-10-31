# Product Definition

Status: draft 0.1. Decisions here are settled for the first version. Open questions are listed at the end.

## In one paragraph

Steelframe is a free, open-source website that gives people preparing for the UPSC Civil Services Examination a daily set of current affairs editorials. Each editorial explains one issue, ties it to the exam syllabus, shows where every claim comes from, and ends with a few questions to help the reader remember it. It is written by an automated pipeline, checked by a second automated pass, and published automatically only if it passes a set of fixed checks.

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
| Publish gate | The fixed checks a draft must pass before it goes live: claims verified, rubric score at least 70, no accuracy failure, topic not on the sensitive list |

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
| 1. Collect | In the morning, the system gathers new items from official sources and news outlets: ministry releases, committee reports, court orders. It removes duplicates. |
| 2. Choose | Each item is scored for exam relevance and linked to a syllabus topic and past questions. Say a ministry has published a draft rule. It scores high. A routine appointment scores low and is dropped. |
| 3. Research | For the draft rule, the system fetches the draft itself, the law it comes under, and earlier background. These are the primary sources. |
| 4. Write | A draft editorial is produced: what changed, the background, the main arguments for and against, a view on whether it will work, the way forward, and a Mains angle. It also produces three recall questions. |
| 5. Check claims | A second, separate pass checks every claim in the draft against its source. Say it finds that one figure in the draft does not match the document. It sends the draft back with that note. |
| 6. Score | The corrected draft is scored against the [quality rubric](QUALITY_RUBRIC.md). Say it scores 78. It passes the minimum of 70 and has no accuracy failure. |
| 7. Publish | The draft passes the publish gate and the editorial appears on the Today page in three depths. Every claim links to its source. |
| 8. Read | In the evening, an aspirant opens it. They read the brief, then the editorial. They tap a figure and see the passage. They highlight a paragraph and answer the three questions. One answer is wrong, so that question returns in the revision queue in a few days. |

If step 5 or step 6 fails twice, the draft is held and the maintainer is alerted. Nothing unchecked goes live.

## Principles that shape the first version

| Principle | Effect |
|---|---|
| Evaluation before features | The app is not built until the writing beats a defined benchmark in blind review |
| Every claim has a source | A claim that cannot be traced does not ship |
| Exam-shaped, not news-shaped | Content is chosen and framed by the syllabus and past papers |
| Checked by machines, audited by people | No human approves each piece. A fixed publish gate decides, and a daily sample of published pieces is audited. A high error rate pauses publishing |
| Respect the sources | We link to and summarise sources within their terms, with no wholesale copying |
| Open | The code and the rubric are public under the Apache License 2.0 |

## The reading experience

This describes the intended feel. The detailed design comes in the design phase.

| Screen | What the reader sees |
|---|---|
| **Today** | About eight issues, ranked by how likely they are to matter for the exam. Each shows its topic, read time and a small relevance bar. The list ends with "that is today", so there is no endless scroll. |
| **Reader** | A calm page built for reading. A reader picks a depth: brief, editorial or deep dive. Claims carry a faint underline. Tapping one opens the source and the passage. Syllabus topics and past questions sit in the margin. The reader can save, highlight and add notes. Three recall questions come at the end. |
| **Syllabus map** | Every syllabus topic as a point, sized by how much news touched it in the last 30 days. Lines join topics that the same event touches. The reader's recent reading is traced across it. Tapping a topic lists its editorials. On weak phones it becomes a flat tile view with the same information. |
| **Revision** | Questions the reader got wrong, returned after a few days. |
| **Account** | Saved items, highlights and notes, a streak calendar, and preferences. |

Design rules:
- Reading comes first. No ads, banners or clutter.
- Motion appears only where it explains something, such as opening a source or zooming the map.
- The site must work well on low-end Android phones.
- The syllabus map is the one showpiece. The rest stays quiet.

## Decisions and the alternatives we ruled out

| Decision | Chosen | Other options, and why not |
|---|---|---|
| How wide is the first version? | Daily GS editorials only | **Add Mains answer feedback:** valuable, but poor feedback would damage trust, so it waits for its own evaluation. **Add test series and courses:** a different product, with a different cost. |
| What do we write from? | Primary documents only in the first version. Newspapers are left out because their terms forbid automated use (see [sources](sources/SOURCES.md)). They can return later with written consent | **One newspaper editorial as the base:** inherits one writer's framing and errors, and its facts are second-hand. **Aggregating news items:** shallow, and repeats whatever the outlets got wrong. |
| Reading depth | Three layers built from one set of sourced claims | **One fixed length:** forces every reader into the same time budget. **Separate pieces per length:** the figures could drift apart. |
| Where saved items live | In a reader account | **Browser storage only:** notes vanish when data is cleared. **No saving:** fails the use case, since saving and highlighting matter to aspirants. |
| What the syllabus map shows | What has been in the news, by topic | **A "percent of syllabus covered" tracker:** misleading, since current affairs has no finish line. **No map:** loses the one view that shows how issues connect. |
| Who approves publication | An automatic publish gate, plus a daily sampled audit after publishing | **A human editor for every piece:** safest, but slow, and it caps how many editorials a day. This is a proof of concept built to production standard, so the gate and the audit carry the safety instead. **Fully automatic with no audit:** errors would go unmeasured. |

## What can go wrong

| Risk | What it would look like | How we respond |
|---|---|---|
| A factual error is published | A wrong figure or attribution reaches readers | The claim check and the accuracy gate come first. If one still gets through, we correct it visibly, with the date and a note |
| A source disappears or changes after we cite it | The link to the passage breaks, or shows different text | Keep a dated copy of the cited passage where the source's terms allow it, and show it alongside the link |
| A copyright or terms complaint | A source owner objects to our use | Use official government texts first, summarise instead of copying, and take down on request. The reuse limits of each source are checked before it is used |
| The pipeline or a source is down | No edition for the day | Say so openly. Do not publish a partial or unchecked edition. A failed run is retried, and an outage is never reported as "done" |
| Quality drifts as models or sources change | Scores fall slowly | The examiner scores every piece, and the benchmark is re-run on a schedule |
| Reviewers disagree | Rubric scores are noisy | Measure agreement per dimension, and revise unclear score descriptions before relying on them |
| The publish gate lets an error through | A wrong claim goes live with no person having read it | Audit a daily random sample of published pieces. If the error rate passes the limit, pause publishing. Correct visibly, with the date and a note |
| Aspirants do not switch | Low return visits in the closed beta | Treat retention as the main test of the first release, and learn why before adding features |
| Cost per editorial runs away | A heavy day multiplies calls | Set a cost limit per piece, count calls per item at normal load and during failures, and avoid retrying errors that cannot succeed |
| A sensitive topic is handled badly | A politically charged story is framed one-sidedly | Show competing views as views, with their sources, and hold sensitive topics for the maintainer instead of publishing them automatically |

## What is still open

| Question | Notes |
|---|---|
| What may we reuse from each government and court source? | To be answered source by source in the knowledge base phase |
| What goes on the sensitive-topic list, and what is the error rate that pauses publishing? | To be set from the first audits |
| What is the target cost per editorial? | To be set after the first pipeline run |
| How is the project sustained, given it is free and open source? | Not decided. Pricing stays out of the first version |
| How are corrections shown to readers? | The need is settled. The design is not |
| How do readers sign in, and what do we store about them? | Needs a privacy review before accounts are built |
| Should Hindi be added, and when? | Depends on proving quality in English first |
| How are reviewers recruited for blind review? | An evaluation-phase task |
