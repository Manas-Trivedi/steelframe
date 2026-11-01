# App stack decision

Status: decided 1 November 2026, without a call with the maintainer. Each choice marked "assumption" can be reversed cheaply. Code: `steelframe/site/`, `site/`.

## What this is for

The pipeline produces published editorials in a database. This note decides how readers see them: what the site is built with, where it runs, where the reader's own data lives, and what runs the daily pipeline. The rule throughout is the one for models: **free, with no exceptions**.

## Terms

| Term | Meaning |
|---|---|
| Static site | Pages made ahead of time as plain files. No server code runs when a reader visits |
| Site generator | The program that turns the database into those pages (`python3 -m steelframe.site.build`) |
| localStorage | A small store inside the reader's own browser. It never leaves the device |
| Scheduler | Something that starts the daily run at a set time. GitHub Actions has one, free for public repositories |
| Cold start | The delay when a sleeping server wakes for its first visitor. A static site has none |

## The key idea

**Make the whole site ahead of time, and keep each reader's own data in their own browser.**

The product has no device sync in v1 (decided in the product definition). So a reader's saves, highlights, notes, streak and preferences need no server and no login. That removes the database, the sign-in system, the hosting bill and most of what can break. The daily run writes new pages; readers download them.

## The stack

| Part | Choice | Why |
|---|---|---|
| Pages | Plain HTML and CSS written by a Python generator with no dependencies | Fast on weak phones, works offline once loaded, nothing to patch |
| Interaction | About 300 lines of plain JavaScript in one file | Source drawer, depth switch, quiz, highlights. A framework would be larger than the rest of the site |
| Reader data | localStorage | Free, private, works without sign-in |
| Hosting | A free static host: GitHub Pages (assumption) | Free, simple, HTTPS |
| Pipeline state | The SQLite file, kept on a `state` branch of the repository (assumption) | The scheduler has no disk that lasts between runs. The file is small |
| Scheduler | GitHub Actions on a daily cron, switched off until the maintainer sets a variable and the three API keys | Free for public repositories. Does nothing until switched on |
| Model access | Gemini, Groq and OpenRouter free tiers, through the router | Already built |

## Choices considered

### How the site is made

| Option | For | Against | Verdict |
|---|---|---|---|
| A. Static pages from a small generator, plain JavaScript | Free, fast, no server to run or secure, easy to test | Anything shared between readers (comments, sync) needs another part later | **Chosen** |
| B. A React or Next.js app with a server and Postgres | Accounts with sync, rich interaction, what most teams would pick | A server and a database to run, free tiers sleep or cap, auth to secure, far more code, and sync is out of v1 | Ruled out for now |
| C. A ready-made generator (Hugo, Eleventy) | Mature, many themes | A second language and toolchain to learn for pages that need a custom reader and a custom checker. Our data comes from SQLite, not Markdown | Ruled out |
| D. A hosted CMS or Notion export | No code | Cannot show per-claim sources, the drawer or the quiz | Ruled out |

### Where the reader's data lives

| Option | For | Against | Verdict |
|---|---|---|---|
| A. In the browser (localStorage) | No server, no login, private | Lost if the reader clears the browser. Not shared across devices | **Chosen**, matches "no device sync" in v1 |
| B. A free hosted database with sign-in | Sync across devices | Needs accounts, a privacy policy and an abuse plan. Out of v1 | Later |
| C. A file the reader exports and imports | Gives the reader a backup | Awkward | Add a "download my data" button now, as a safety net |

### Where the daily run lives

| Option | For | Against | Verdict |
|---|---|---|---|
| A. GitHub Actions cron | Free, logs, secrets, can also publish the site | Jobs can start late. Public logs (keys are masked). 6-hour job limit | **Chosen** |
| B. A home machine with cron | No limits | Must be switched on; one point of failure | Fallback |
| C. A cloud function on a free tier | Pay-per-use | Time limits too short for the checks, and each provider's free tier differs | Ruled out |
| D. A small always-on server | Simple | Not free | Ruled out |

### Where the pipeline's state lives

| Option | For | Against | Verdict |
|---|---|---|---|
| A. The SQLite file on a `state` branch | Free, versioned, simple | Binary file in git. A few MB a year | **Chosen** |
| B. A free hosted Postgres | Matches the storage design, vectors with pgvector | Another service, the code uses SQLite features, free tiers pause | Later, when search needs embeddings |
| C. GitHub Actions cache | Easy | Entries are deleted after days of inactivity | Ruled out: it would lose state silently |

## What can go wrong

| Risk | Response |
|---|---|
| A reader clears their browser and loses notes | "Download my data" button. Said plainly on the account page |
| The scheduler is late or skipped | The next run catches up; the daily cap is per calendar day |
| The state branch gets corrupted | The workflow checks the file opens before it saves. Old commits keep every earlier version |
| GitHub changes free terms | The generator makes plain files, so any static host works. The cron can move to a home machine |
| Many readers | A static host scales with no work from us |
| A generated page runs untrusted text | The generator escapes all model output. A test feeds hostile text through it |

## Still open

| Question | Notes |
|---|---|
| Domain name | Using the default GitHub Pages address for now |
| Search across editorials | Not in v1. The syllabus map and the topic lists are the way in |
| Analytics | None. No tracking of readers. Revisit with the beta |
| Sync across devices | After the beta, if readers ask |
