"""The scoring rubric from docs/QUALITY_RUBRIC.md as data. A test keeps the weights in step with the document."""

PASS_TOTAL = 70
ACCURACY_FLOOR = 2  # accuracy at or below this fails the draft whatever the total

# key, name, weight, anchors for 1 / 3 / 5
DIMENSIONS = [
    ("accuracy", "Accuracy", 25,
     "a claim is wrong or cannot be traced to any source",
     "claims are true but some cannot be traced to a primary source, or a figure is slightly off",
     "every claim is true and linked to a primary source"),
    ("judgment", "Judgment", 20,
     "a list of points with equal weight, no view on what matters",
     "some points are ranked, or one counterargument is shown",
     "says which points matter most and why, shows the strongest counterargument, states whether the measure is likely to work"),
    ("evidence", "Evidence quality", 10,
     "examples are hypothetical or vague",
     "examples are real but undated or lack figures",
     "every example is real, dated and specific, with a figure where one exists"),
    ("exam_fit", "Exam fit", 10,
     "reads like news; an aspirant could not build an answer from it",
     "covers the main angles but leaves out some an answer would need",
     "covers what exists, what is new, what is wrong, what to do and a Mains angle, with Prelims facts separated"),
    ("linking", "Linking", 10,
     "no syllabus or past-question links",
     "a syllabus topic is named, but past-question links are missing or loose",
     "each point is tied to its syllabus topic and past questions are linked to the points that answer them"),
    ("consistency", "Consistency", 10,
     "the same measure carries different figures",
     "figures agree but terms or units change between sections",
     "figures, names and units are identical everywhere, including across the brief and the long version"),
    ("readability", "Readability", 10,
     "hard to follow, or far longer than the stated reading time",
     "clear but dense, or poorly paced",
     "clear, well paced, matches the stated reading time, and a shorter or longer version is available"),
    ("india_link", "India link", 5,
     "no link to India",
     "mentions India but not the relevant law, institution or case",
     "names the relevant Indian law, institution and case, and what it means for India"),
]
KEYS = [d[0] for d in DIMENSIONS]
WEIGHTS = {d[0]: d[2] for d in DIMENSIONS}


def total(scores):
    """scores: {key: int 1..5}. Returns the weighted total out of 100."""
    return round(sum(WEIGHTS[k] * scores[k] / 5 for k in KEYS), 1)


def passes(scores):
    return total(scores) >= PASS_TOTAL and scores["accuracy"] > ACCURACY_FLOOR


def anchors_text():
    lines = []
    for key, name, weight, low, mid, high in DIMENSIONS:
        lines.append(f"{key} ({name}, weight {weight}): 1 = {low}. 3 = {mid}. 5 = {high}. 2 and 4 sit between.")
    return "\n".join(lines)
