"""Check the tag files against the topic list and print a summary.

Reads data/past_papers/tags/*.tsv and data/syllabus/gs_topics.yaml. Needs PyYAML.
Prints, per paper, how many questions are tagged and what share need recent news.
"""
import csv, glob, os, collections
import yaml

topics = {t["id"]: t for t in yaml.safe_load(open("data/syllabus/gs_topics.yaml"))["topics"]}
rows = []
bad = []
for f in sorted(glob.glob("data/past_papers/tags/*.tsv")):
    year, stage, paper = os.path.basename(f)[:-4].split("_")
    for r in csv.DictReader(open(f), delimiter="\t"):
        if r["topic"] not in topics:
            bad.append((f, r["n"], r["topic"]))
        if r["ca"] not in ("y", "n"):
            bad.append((f, r["n"], "ca=" + r["ca"]))
        rows.append((year, stage, paper, r["topic"], r["ca"]))
if bad:
    raise SystemExit(f"invalid tags: {bad}")
by = collections.defaultdict(list)
for y, s, p, t, c in rows:
    by[(y, s, p)].append((t, c))
print("paper                     tagged  current-affairs")
for k in sorted(by):
    v = by[k]
    ca = sum(1 for _, c in v if c == "y")
    print(f"{k[0]} {k[1]:8} {k[2]:5}  {len(v):6}  {ca:3} ({100 * ca // len(v)}%)")
