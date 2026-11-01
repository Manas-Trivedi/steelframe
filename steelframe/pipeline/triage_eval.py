"""Check Triage against the hand-labelled items in data/triage/labels.csv.

    python3 -m steelframe.pipeline.triage_eval

Pass bars (docs/pipeline/TRIAGE.md): keep/drop agreement at least 85%, and no labelled keep (relevance 2 or 3)
dropped by the model. A missed keep is worse than a wasted one, because a dropped story is never seen again.
"""
import csv
import sys

from ..taxonomy import load_topics
from .common import build_router
from .triage import BATCH, KEEP_AT, triage_titles

LABELS = "data/triage/labels.csv"


def score(labels, predictions):
    """labels: [(relevance, topic)]; predictions: [(relevance, topic)] in the same order."""
    n = len(labels)
    exact = sum(p[0] == l[0] for l, p in zip(labels, predictions))
    near = sum(abs(p[0] - l[0]) <= 1 for l, p in zip(labels, predictions))
    keep_agree = sum((p[0] >= KEEP_AT) == (l[0] >= KEEP_AT) for l, p in zip(labels, predictions))
    keeps = [(l, p) for l, p in zip(labels, predictions) if l[0] >= KEEP_AT]
    missed = sum(p[0] < KEEP_AT for _, p in keeps)
    topic_ok = sum(p[1] == l[1] for l, p in keeps)
    return {"n": n, "exact": exact / n, "within_one": near / n, "keep_agreement": keep_agree / n,
            "labelled_keeps": len(keeps), "missed_keeps": missed,
            "topic_match_on_keeps": topic_ok / len(keeps) if keeps else None}


def main():
    rows = list(csv.DictReader(open(LABELS, encoding="utf-8")))
    labels = [(int(r["relevance"]), r["topic"]) for r in rows]
    router, topics = build_router(), load_topics()
    predictions, models = [], set()
    for i in range(0, len(rows), BATCH):
        got, model = triage_titles(router, [r["title"] for r in rows[i:i + BATCH]], topics)
        predictions += [(g[0], g[1]) for g in got]
        models.add(model)
    for row, label, pred in zip(rows, labels, predictions):
        flag = "" if (label[0] >= KEEP_AT) == (pred[0] >= KEEP_AT) else "  <-- keep/drop differs"
        print(f"label {label[0]} {label[1]:10} model {pred[0]} {pred[1]:10} {row['title'][:60]}{flag}")
    result = score(labels, predictions)
    print(f"\nmodels: {sorted(models)}")
    print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in result.items()})
    ok = result["keep_agreement"] >= 0.85 and result["missed_keeps"] == 0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
