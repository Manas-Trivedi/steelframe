# Sources: what we read and what we may reuse

Status: draft 0.2, updated 31 October 2026 after the terms pages were checked in a browser. This is a reading of each source's published terms, not legal advice. The machine-readable list is in `data/sources/sources.csv`.

## Why this exists

Steelframe writes each editorial from original documents. Before the pipeline can fetch anything, we need to know three things for every source: what it gives us, how we may get it, and how much of it we may keep or show. This note answers those.

## Terms used here

| Term | Meaning |
|---|---|
| Primary source | The original document: a law, a judgment, a report, a press release |
| Secondary source | A newspaper or analysis that reports on primary sources |
| Reproduce | Copy the text, in part or in full, onto our site or into our data |
| Summarise | Say it in our own words, with a link to the original |
| Passage copy | A dated copy of the cited passage, kept so a claim can still be checked if the source changes |
| Attribution | Naming the source and linking to it |
| s52(1)(q) | A rule in India's Copyright Act, 1957 that lets anyone reproduce Gazette matter (except Acts), reports laid before a legislature, and court judgments and orders, unless the body concerned forbids it |

## The rule we follow

| What we do | When |
|---|---|
| Link and credit the source | Always |
| Summarise in our own words | Always |
| Keep a short passage copy and show it beside the claim | Only where the terms below allow it |
| Reproduce long text | Never, except where the source's own terms allow it |
| Use newspapers | Not in the first version. The Indian Express forbids bots, summaries and AI use. The Hindu's terms are unread. See below |

Facts, such as a date or a figure, can be used freely. The wording around them is what is protected.

## The sources

| Source | Gives us | What its terms allow | Passage copy? | Verdict |
|---|---|---|---|---|
| **PIB** (Press Information Bureau) | Press releases, backgrounders | Free reproduction, no prior approval, if accurate, not misleading, and credited. Third-party material excluded. **Confirmed on the live page** | Yes | Use |
| **PRS Legislative Research** | Bill summaries, analyses, trackers | Non-commercial reuse, in part or in full, with credit. Footer says CC BY 4.0 | Yes, with credit | Use |
| **data.gov.in** | Government datasets | GODL-India: use allowed, credit the provider, no implied endorsement. Excludes personal data and logos | Yes, with credit | Use |
| **Court judgments** (Supreme Court, High Courts) | Judgments, orders | s52(1)(q) allows reproduction unless the court forbids it. **Supreme Court site confirmed:** credit the source, no misleading or derogatory use, third-party material excluded. It also says its documents are "for reference only" and not a legal document | Yes, with credit | Use |
| **eGazette** | Rules, notifications | Publisher claims copyright. s52(1)(q) covers Gazette matter except Acts | Short quotes | Use with care |
| **India Code** | Text of central Acts | Site has moved to indiacode.gov.in. New terms not read yet. An Act's text can be reproduced only with commentary | Short quotes | Use with care |
| **Parliament** (committee reports, debates) | Standing committee reports, questions and answers | No site terms found. s52(1)(q) covers reports laid before a legislature | Short quotes | Use with care |
| **RBI** | Policy statements, circulars, Bulletin, data | "All rights reserved". Disclaimer prohibits caching and framing, and asks for written notice before linking | No | Link and summarise only |
| **The Hindu** | Reporting, editorials | Terms page not found. Assume the same limits as The Indian Express | No | **Not used** until the terms are read |
| **The Indian Express** | Reporting, explainers | Read in full. Section 9.3 bans bots, crawlers and scrapers, summaries and derivative works, AI use and training, and caching. Written consent or a paid licence is needed | No | **Not used** |

## Example run

Say the Finance Ministry issues a press release on a new rule, and the Gazette carries the notification.

| Step | What the system does | Why it is allowed |
|---|---|---|
| 1 | Reads the PIB release and keeps a dated copy of the key paragraph | PIB allows reproduction with credit |
| 2 | Reads the Gazette notification and quotes one clause | s52(1)(q) covers Gazette matter. We keep the quote short |
| 3 | Finds the ministry's own note on how the rule was drafted | Another primary source, with its own terms |
| 4 | Writes the editorial in its own words, each claim linked to PIB or the Gazette | Credit and links on every claim |

## What can go wrong

| Risk | Response |
|---|---|
| A source's terms are not what we read | Each row records when and how we checked it. Re-check on a schedule, and take content down on request |
| Government sites block our fetcher | Seen on 31 Oct 2026: several returned "403 Forbidden" to an automated fetch. Use polite, slow fetching, official feeds where they exist, and alert when a source fails. A source that fails must never be reported as "no news today" |
| RBI objects to links or copies | We link to the page and keep no copy, and we ask RBI for written permission |
| Newspaper terms forbid automated reading | The Indian Express forbids it outright, so newspapers are left out of the first version. Re-open only with written consent |
| A source changes or removes a page | The passage copy (where allowed) keeps the claim checkable |

## What was checked, and how

| Source | How we read the terms | Gap |
|---|---|---|
| PRS | Read the disclaimer page directly | None |
| RBI | Read the disclaimer page directly | Older RBI pages say something looser. The current page is stricter, so we follow it |
| PIB | Policy text pasted from the live page | None. Matches |
| Supreme Court | Policy text pasted from the live page | None. Matches. Adds the "reference only" warning |
| data.gov.in | The licence page returned 404 | Find the new address of the licence page |
| India Code | Site moved to indiacode.gov.in | Read the new site's policy |
| NCERT | Only a search engine's AI summary, not NCERT's own notice | Find NCERT's own notice, or email secy.ncert@nic.in |
| eGazette, Parliament | No reuse policy found | Ask, or confirm by reading the site footers |
| The Indian Express | Terms pasted in full | None |
| The Hindu | Terms page not found | Find it, or leave The Hindu out |

## Can the pipeline reach each source?

Tested on 31 October 2026 from one home network, with a plain script that names itself in its user agent.

| Source | Result | Meaning |
|---|---|---|
| RBI press release feed | Works | 10 items |
| The Hindu and Indian Express feeds | Work technically | Switched off. The terms do not allow our use |
| PIB release feed | **Blocked** | First attempt timed out. Second returned 403 Forbidden |
| data.gov.in, India Code | **Blocked** | 403 Forbidden |
| NCERT, Parliament e-library, Supreme Court main site | Timed out | Not tried again |
| PRS, eGazette home page | Works | No feed. Pages must be read |

PIB is the most important primary source, so a blocked PIB is the main risk for the Scout stage. The fix is to be settled before Scout can rely on it: see the open questions below.

## What is still open

| Question | Notes |
|---|---|
| What are the data.gov.in licence terms, and India Code's new policy? | The old data.gov.in page is gone and India Code has moved |
| What are the Parliament and eGazette reuse terms? | Not published where we looked |
| Will RBI allow links and short quotes? | Ask in writing |
| Do we ever want newspapers? | Only with written consent or a licence. Email corporate@indianexpress.com for The Indian Express. The product works without them |
| Does a dated passage copy count as "caching" for sources that forbid it? | Treated as yes for RBI. Confirm for others |
| Which official feeds and APIs exist for each source? | Feeds found for PIB, RBI and both papers. None found for PRS or eGazette |
| How do we read PIB if it keeps blocking scripts? | Options: run the fetch from a network PIB accepts, ask PIB for access, or find an official mirror. Not decided |
