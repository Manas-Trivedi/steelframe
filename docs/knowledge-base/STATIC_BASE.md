# Static base: linking news to standard knowledge

Status: draft 0.1, written 31 October 2026. A reading of public notices, not legal advice.

## What this is for

An editorial on a news item also has to explain the idea behind it. A story on a new rule for village councils needs a line on what a Panchayat is and where the Constitution creates it. That background is standard textbook knowledge, not news. We call it the **static base**.

This note says how the system finds that background, shows it to the reader, and stays within what the book publishers and the government allow.

## Terms used here

| Term | Meaning |
|---|---|
| Static base | Standard knowledge that does not change with the news: the Constitution, key Acts, NCERT school textbooks, core concepts |
| NCERT | The National Council of Educational Research and Training. Its school textbooks are the base text for most aspirants |
| Concept note | A short explainer we write ourselves, about 80 to 120 words, on one standard idea |
| Reference | A pointer to where the idea is set out: a Constitution article, an Act section or an NCERT chapter |
| Concept index | The table that maps each syllabus topic to its concept notes and references |

## What NCERT allows

| Point | What the public notices say |
|---|---|
| Download and read | Books and chapters may be downloaded and used as textbooks or for reference |
| Republish | Strictly prohibited |
| Hosting on other sites | Reported as not permitted. Links may need written permission (from a secondary source) |
| Commercial reuse | Needs permission. NCERT has issued warnings in 2024 and 2026 against copying its books |
| Pages | Carry a watermark declaring NCERT's copyright |

We did not find the full NCERT copyright notice. The summary above comes from news reports and press releases, so it is second-hand. Treat NCERT as **link and summarise only**: no stored chapter text, no passage copies, no quotes beyond a short phrase.

## The idea

**Keep a small index of pointers and our own short notes. Never keep the books.**

For each of the 65 syllabus topics in [gs_topics.yaml](../../data/syllabus/gs_topics.yaml), the concept index holds:

| Field | Example (illustrative) |
|---|---|
| Topic id | `G2.GOV` |
| Concept note | Our own 100-word explainer, with its references |
| References | Constitution article or Act section (link to India Code), NCERT chapter (class, book, chapter, link to ncert.nic.in) |
| Linked past questions | From the [tag files](../../data/past_papers/tags/), via `tools/past_papers/questions_for_topic.py` |

The Writer reads the concept note and references for the topic and uses them to write the background. The reader sees the references as "read more" links beside the claim.

## Example run

A ministry publishes a draft rule that gives village councils more power over local funds.

| Step | What happens |
|---|---|
| 1 | Triage tags the item to a syllabus topic, say governance and accountability |
| 2 | The concept index returns the topic's concept note, the Constitution article that creates village councils, and the NCERT chapter on local government |
| 3 | The Writer writes the background paragraph from the concept note, in its own words |
| 4 | Each background claim carries a reference. The reader taps it and goes to the article on India Code, or the NCERT chapter on ncert.nic.in |
| 5 | The Fact-checker confirms each background claim against the cited Act or article. For NCERT references it confirms the chapter covers the claim, using the model's own reading of the chapter fetched at check time and not stored |

## Choices considered

| Option | What it is | For | Against | Verdict |
|---|---|---|---|---|
| A. Pointer index plus our own short notes | Described above | Within NCERT's rules. Every background claim has a source. Small and cheap | Notes must be written and kept correct. Readers must click out to see NCERT's wording | **Chosen** |
| B. Ingest NCERT text and retrieve passages | Store the books in the search index | Best matching. Passage can be shown inline | Breaches the ban on republishing and hosting. Risks a takedown of the whole project | Ruled out |
| C. Rely on the model's memory of the textbooks | No index | Nothing to build | No source for the claim, which breaks the core rule. Errors cannot be traced | Ruled out |
| D. Use open sources (Wikipedia, open government texts) as the base | Link to freely licensed pages | Licence is clear. Passages can be stored with credit | Weaker authority. Not the text aspirants are examined on. Wikipedia's share-alike licence would bind our notes | Possible add-on, not the base |
| E. Only Constitution, Acts and judgments, no NCERT | Primary sources only | Strongest legal footing | Leaves out history, geography, economics and science background, which only textbooks cover | Ruled out as the whole base |

## What can go wrong

| Risk | Response |
|---|---|
| A concept note is wrong | Every note cites a reference. The Fact-checker checks notes the same way as any claim. A daily sample of published pieces is audited |
| NCERT objects to links | Ask in writing. If refused, link to the book's landing page and name the chapter in plain text |
| NCERT changes or reorders chapters, or issues a new edition | Store class, book, title and chapter title, not just a URL. Re-check links monthly |
| A note drifts close to NCERT's wording | Write notes from the Constitution and Acts first. Run a similarity check against the chapter text at write time, not stored |
| Syllabus topics are too coarse to find the right chapter | Several references per topic. Revisit subtopics if the back-test shows poor matches |

## What is still open

| Question | Notes |
|---|---|
| What does NCERT's own copyright notice say, and do links need written permission? | Read the notice on ncert.nic.in and ask NCERT |
| Is it fine to read an NCERT chapter during checking, if we never store it? | Downloading for reference is allowed, but a machine reading it is a grey area. Ask NCERT together with the link question |
| Which NCERT books and chapters do we index first? | Start with the topics that past questions touch most. See the topic counts in [PAST_PAPER_TAGGING.md](../evals/PAST_PAPER_TAGGING.md) |
| Who writes the first 65 concept notes? | The pipeline can draft them. Each is audited with the [accuracy audit](../evals/ACCURACY_AUDIT.md) before use |
| Do we need standard reference books beyond NCERT (for example Laxmikanth, Spectrum)? | They are commercial books, so link-only at most. Decide once the first notes are written |
