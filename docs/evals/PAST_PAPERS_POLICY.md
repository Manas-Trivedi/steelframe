# Past Papers: Reuse Policy

Status: draft 0.1.

## Why this exists

The evaluation phase needs past UPSC Civil Services Examination papers. Aspirants' questions tell us what the exam asks, so the papers drive two things: the back-test (would our coverage have matched what was asked?) and the past-question links in each editorial.

The Union Public Service Commission (UPSC) owns the papers. This note records what its website allows, and how the project handles the papers as a result.

## What the UPSC website says

From the [Website Policies](https://www.upsc.gov.in/website-policy) page, read on 30 October 2026:

| Topic | What it says |
|---|---|
| Copying material | Material on the site "may be reproduced free of charge after taking proper permission" |
| How it must be reproduced | Accurately, without changing the content, not in a derogatory way, and not in a misleading context |
| Credit | The source must be prominently acknowledged |
| Third-party material | Not covered by that permission |
| Linking to the site | Allowed with no prior permission. UPSC asks to be informed of links, and does not allow its pages to be loaded inside frames on another site |

The site's [Disclaimer](https://www.upsc.gov.in/disclaimer-) warns organisations against using the UPSC name or abbreviation in their own name, trade name or description of their activity.

## What this means for the project

| Question | Answer |
|---|---|
| Can we link to the official papers? | Yes. Linking needs no permission. We open them in a new window and never in a frame |
| Can we store the question text in this repository? | Not without permission. The policy requires permission to reproduce |
| Can we store our own tags about each question? | Yes. A tag such as "year, paper, question number, topic" is our own data, and it links to the official paper |
| Can we show question text inside the app? | Not until permission is granted. Until then the app shows the reference and a link, not the text |
| Can we use the papers privately to build and test the tagging? | We read them locally for analysis. We do not publish or redistribute them. This is a reading of the policy and not legal advice |
| Can we use the name "UPSC"? | Only to describe what the exam is. Never in the project name, a trade name or a claim of connection |

## Storage rules

1. The repository holds links, our tags and our topic taxonomy. It never holds question text or the official PDFs.
2. Downloaded PDFs and extracted text stay in a local folder that is excluded from version control.
3. Any page that shows a past question links to the official paper and names UPSC as the source.
4. The README states that the project is not affiliated with UPSC.

## Open

| Question | Notes |
|---|---|
| Should we ask UPSC for permission to show question text? | Likely worth doing before the app shows questions. The policy describes permission as free. It needs a written request, and someone with standing to make it |
| What do we do if permission is refused? | Keep showing the reference and link, with a short paraphrase of the topic the question tested. Paraphrases must be checked against the policy |
| Does the same rule apply to coaching-institute copies of past papers? | Treated as third-party material. We do not use them |
