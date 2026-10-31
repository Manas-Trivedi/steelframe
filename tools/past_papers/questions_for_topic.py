"""List past questions for a syllabus topic, with a link to the official paper.

Usage: python3 tools/past_papers/questions_for_topic.py TOPIC [--ca y|n]

TOPIC is a topic id from data/syllabus/gs_topics.yaml, or a prefix such as G3.
Reads data/past_papers/tags/*.tsv and data/past_papers/index.csv. No question
text is stored, so the output is year, paper, number and the official link.
"""
import argparse, csv, glob, os

ap = argparse.ArgumentParser()
ap.add_argument("topic")
ap.add_argument("--ca", choices=["y", "n"])
args = ap.parse_args()

links = {(r["year"], r["stage"], r["paper"]): r["official_url"]
         for r in csv.DictReader(open("data/past_papers/index.csv"))}
hits = []
for f in sorted(glob.glob("data/past_papers/tags/*.tsv")):
    year, stage, paper = os.path.basename(f)[:-4].split("_")
    for r in csv.DictReader(open(f), delimiter="\t"):
        if r["topic"].startswith(args.topic) and (not args.ca or r["ca"] == args.ca):
            hits.append((year, stage, paper, r["n"], r["topic"], r["ca"]))
for year, stage, paper, n, topic, ca in hits:
    print(f"{year} {stage} {paper} Q{n}\t{topic}\tca={ca}\t{links.get((year, stage, paper), '')}")
print(f"{len(hits)} questions")
