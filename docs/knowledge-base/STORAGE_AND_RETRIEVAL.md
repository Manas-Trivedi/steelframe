# Storage and retrieval

Status: draft 0.1, written 31 October 2026. Sizes and costs are estimates to be checked on the first real run.

## What this is for

The pipeline needs a memory. It must remember what it has already read today, find earlier material that explains a new story, and keep the exact passage behind every claim so a reader can tap it. This note decides where that memory lives and how the pipeline searches it.

## Terms used here

| Term | Meaning |
|---|---|
| Item | One thing fetched from a source: a press release, a judgment, a report |
| Chunk | A piece of an item, about a page long, stored and searched on its own |
| Embedding | A list of numbers that stands for the meaning of a chunk, so similar chunks sit close together |
| Vector search | Finding chunks whose embeddings are close to a question's embedding |
| Full-text search | Finding chunks that contain the words asked for |
| Hybrid search | Running both searches and merging the results |
| Passage copy | A dated copy of the text behind a claim, kept only where [the source's terms](../sources/SOURCES.md) allow |
| Claim record | One claim in an editorial, with a pointer to its source and passage |
| Scout, Triage, Researcher, Writer, Fact-checker | The pipeline stages described in the [README](../../README.md) |

## What gets stored

| Data | Size and life | Where |
|---|---|---|
| Raw fetched files (PDFs, pages) | Large. Kept 30 days, then deleted | Object storage or local disk, outside the database |
| Items kept after Triage | Small. Kept for good | Database |
| Chunks and embeddings of kept items | Small. Kept for good | Database |
| Passage copies | Tiny. Kept while the editorial is live | Database, only for sources that allow it |
| Editorials, claim records, scores | Tiny. Kept for good | Database |
| Reader accounts, saves, highlights, streaks | Small. Kept until deleted by the reader | Database, separate tables |
| Syllabus topics, past-question tags, concept index | Tiny. Edited by hand | Files in the repository |

Only items that pass Triage are chunked and embedded. Raw fetches that Triage drops are never indexed. This keeps the database small enough for a free tier.

## The key idea

**One Postgres database holds everything that is searched or served. Raw files live outside it and expire.**

Postgres can do full-text search and vector search in the same query (with the `pgvector` extension), and it can also hold the accounts the product needs anyway. One system covers all of it.

## How the pipeline uses it

| Question the pipeline asks | Stage | How it is answered |
|---|---|---|
| Have we seen this already? | Scout | Same URL or same content hash: exact match. Near-copy of a story from the last few days: nearest-neighbour search on item embeddings. The distance cutoff is set from a hand-labelled sample, not guessed |
| What background do we already hold on this issue? | Researcher | Hybrid search over kept chunks, limited to dates before today and to primary sources first, merged by rank |
| What are the standard references for this topic? | Writer | Look up the topic in the [concept index](STATIC_BASE.md) |
| Which past questions touch this topic? | Triage, Writer | `tools/past_papers/questions_for_topic.py` |
| Where does this claim come from? | Fact-checker, reader | Claim record points to the item and, if allowed, to a passage copy |
| What was in the news for this topic in the last 30 days? | Syllabus map | Plain query on editorials by topic and date |

## Example run

| Step | What happens |
|---|---|
| 1 | Scout fetches 150 items. It records one `source_run` per source, with a status. Two are exact duplicates and are dropped |
| 2 | Triage keeps 12. Only these 12 are chunked, embedded and stored. Raw files for the other 138 stay in the 30-day cache |
| 3 | For a draft rule on village councils, the Researcher searches the database: the last two drafts from the same ministry and a Standing Committee report come back |
| 4 | The Writer drafts. Each claim becomes a claim record pointing to a PIB item and a passage copy |
| 5 | The Fact-checker follows each pointer, reads the passage copy and confirms the claim |
| 6 | The reader taps a figure and the site shows the passage copy, its date and a link to the original |

## Choices considered

| Option | What it is | For | Against | Verdict |
|---|---|---|---|---|
| A. One Postgres with `pgvector` and full-text, raw files outside | Described above | One system to run. Accounts need a database anyway. Filters by date, source and topic combine with vector search in one query. Free tiers exist | Postgres is not the fastest vector store. Free tiers cap size | **Chosen** |
| B. SQLite file with full-text and a vector extension | A single file in the repository or on the host | Simplest. No server | Accounts and a web app writing at the same time as the pipeline need a server database anyway. Two stores then | Ruled out |
| C. Postgres for the app plus a dedicated vector database | Qdrant, Pinecone and similar for search | Faster at large scale. Rich search features | A second service to run, pay for and keep in sync. The data is far too small to need it | Ruled out for now |
| D. No index: fetch and read live each day | Give the model whole documents each time | Nothing to store | No memory for dedupe, no history for background, and a claim cannot point to a stable passage. Cost grows with every re-read | Ruled out |

**When to revisit:** if the database passes the free-tier cap, or a search takes more than a second on the real data, move the vectors to option C and keep the rest.

## Size estimate

These are estimates. Replace them with measured numbers after the first run.

| Quantity | Estimate | Basis |
|---|---|---|
| Items fetched per day | 150 to 300 | Government feeds are the bulk |
| Items kept per day | 10 to 20 | Triage keeps the exam-relevant few |
| Kept items per year | 4,000 to 7,000 | 365 days of the above |
| Chunks per kept item | about 5 | A few pages each |
| Chunks per year | 20,000 to 35,000 | Product of the two |
| Vector size | 0.5 to 6 KB per chunk | Depends on the embedding model and whether half-precision is used |
| Vector storage per year | 10 to 210 MB | Product of the above |

So the vectors alone should fit one to several years inside a small free database. The raw-file cache is the big item, which is why it sits outside the database and expires.

## Technical section

### Tables

| Table | Key columns |
|---|---|
| `source` | id, name, tier, terms_summary, can_store_passage, terms_checked_on |
| `source_run` | id, source_id, started_at, status (`ok`, `partial`, `failed`), items_found, error |
| `item` | id, source_id, url, content_hash, published_at, fetched_at, title, topic_id, relevance_score. Unique on (url, content_hash) |
| `chunk` | id, item_id, position, text, embedding, embedding_model |
| `passage_copy` | id, item_id, text, fetched_at. Rows exist only when `source.can_store_passage` is true |
| `editorial` | id, topic_id, published_at, rubric_score, status |
| `claim` | id, editorial_id, text, item_id, passage_copy_id (nullable), check_status |
| `app_user`, `saved_item`, `highlight`, `streak_day` | Reader data, in tables with no link to the pipeline tables except the editorial id |

Indexes: full-text index on `chunk.text`, vector index on `chunk.embedding`, and plain indexes on `item.published_at`, `item.topic_id` and `claim.editorial_id`.

### Rules that follow from the engineering checklist

| Rule | Why |
|---|---|
| A source fetch that fails writes `source_run.status = 'failed'`. The run is never reported as "no news" | An outage must be visible and retried |
| Retry only on network errors, 5xx and 429. Never retry other 4xx | A 403 from a government site will not succeed on retry. Record it and alert |
| Inserts are idempotent on (url, content_hash) | A retried run must not double the data |
| Embeddings are requested in batches off the main loop, and a failed batch fails the step | No half-embedded item is marked as done |
| Stream rows when reading in bulk. Never load whole tables | Keeps memory flat as data grows |
| Store `embedding_model` on every chunk | Changing the model means re-embedding, and the table must say which rows are old |
| Calls per kept item: one embedding batch plus the stage calls. During an outage, no fallback loops | Cost is the same on a bad day as on a normal day |

### Takedown and deletion

| Event | Action |
|---|---|
| A source asks us to remove its content | Delete its `passage_copy` rows and chunks, mark affected claims `source_removed`, and keep the link |
| A reader deletes their account | Delete the `app_user` row and cascade to their saves, highlights and streak days |
| The 30-day cache expires | A scheduled job deletes the raw files and nothing else |

## What can go wrong

| Risk | Response |
|---|---|
| Free tier fills up | Alert at 70% of the cap. Fall back to option C for vectors |
| Near-duplicate cutoff is too loose or too tight | Tune on a labelled sample. Report both kinds of error |
| Search returns old or superseded material | Filter by date and prefer the newest primary item. Store `supersedes` when a rule is amended |
| Embedding service down | The step fails and retries. No item is marked done without its chunks |
| A passage copy is kept after its source changed terms | Re-check each source's terms on a schedule. `terms_checked_on` shows how stale it is |

## What is still open

| Question | Notes |
|---|---|
| Which embedding model, and what size? | Part of the model choice in the pipeline design doc (D4.1). Row-level `embedding_model` keeps this reversible |
| Where do raw files live: object storage or local disk? | Depends on where the pipeline runs |
| Which host and which free tier? | Decide with the app stack in D6.1 |
| What near-duplicate cutoff works? | Needs a labelled sample from the first Scout run |
| Privacy and retention for reader data | Needs a review before accounts are built, as noted in the product definition |
