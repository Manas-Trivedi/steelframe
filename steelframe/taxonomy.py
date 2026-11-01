"""Read the syllabus topic list and the past-question tags. Standard library only."""
import csv
import glob
import os

TOPICS_PATH = "data/syllabus/gs_topics.yaml"
TAGS_GLOB = "data/past_papers/tags/*.tsv"


def _value(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        text = text[1:-1].replace("''", "'")
    return text


def load_topics(path=TOPICS_PATH):
    """Return [{"id", "paper", "name", "covers"}, ...] from the flat YAML list. No PyYAML needed."""
    topics = []
    in_list = False
    for line in open(path, encoding="utf-8").read().splitlines():
        if line.startswith("topics:"):
            in_list = True
        elif in_list and line.startswith("- "):
            topics.append({})
            line = line[2:]
        elif not in_list or not line.startswith("  "):
            continue
        key, _, value = line.strip().partition(":")
        if topics and key in ("id", "paper", "name", "covers"):
            topics[-1][key] = _value(value)
    if not topics or any("id" not in t for t in topics):
        raise ValueError(f"{path}: no topics found or a topic has no id")
    return topics


def past_questions(topic, tags_glob=TAGS_GLOB):
    """Return [(year, stage, paper, question_number, ca)] tagged to this topic id."""
    hits = []
    for path in sorted(glob.glob(tags_glob)):
        year, stage, paper = os.path.basename(path)[:-4].split("_")
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                if row["topic"] == topic:
                    hits.append((year, stage, paper, row["n"], row["ca"]))
    return hits
