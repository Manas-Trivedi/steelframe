"""Checks that need no model: quote, link and figure. A claim that fails any of them fails the draft.

Quote check: each claim's quote must appear in its passage, character for character. Only whitespace and
typographic quotes and dashes are normalised, because the model cannot be expected to reproduce a double space.
Link check: each claim's passage must be in the pack, and its source must allow a copy.
Figure check: every number in the brief, editorial, deep dive, Mains approach and the stems and explanations of
the recall questions must also appear in a claim or its quote. Analysis may not smuggle in a new figure.
"""
import re

# [c3], [c3, c4], [c3; c5], [c3-c5]: models write citations several ways, so accept them all
MARKER = re.compile(r"\[\s*c\d+(?:\s*(?:,|;|-|\u2013)\s*c?\d+)*\s*\]")
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
TYPOGRAPHY = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
                            " ": " ", " ": " ", " ": " "})


def normalise(text):
    return re.sub(r"\s+", " ", text.translate(TYPOGRAPHY)).strip()


def cited_ids(text):
    """Claim numbers cited in a text: '[c1] ... [c3, c4]' -> {1, 3, 4}. A range [c3-c5] means 3, 4 and 5."""
    ids = set()
    for marker in MARKER.findall(text):
        previous, dash = None, False
        for token in re.findall(r"\d+|[-\u2013]", marker):
            if token.isdigit():
                number = int(token)
                if dash and previous is not None:
                    ids |= set(range(previous, number + 1))
                ids.add(number)
                previous, dash = number, False
            else:
                dash = True
    return ids


WORDS = {w: str(n) for n, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen twenty".split())}
LIST_NUMBER = re.compile(r"(?m)^\s*(?:\d{1,2}[.)]|\(\d{1,2}\))\s+")  # "1. Statement" is numbering, not a figure


def numbers_in(text, words=False):
    """Numbers as plain digit strings: '1,09,019' -> '109019', '31st' -> '31', 'Rs. 12.50' -> '12.50'.

    List numbering at the start of a line is ignored. With words=True, 'seven' counts as 7 (used on claims,
    so a claim that says 'seven' covers a text that says '7').
    """
    text = LIST_NUMBER.sub("", MARKER.sub("", text))
    found = {token.replace(",", "").rstrip(".") for token in NUMBER.findall(text)}
    if words:
        found |= {WORDS[w] for w in re.findall(r"[a-z]+", text.lower()) if w in WORDS}
    return found


def quote_check(draft, pack):
    by_id = {f"P{p['id']}": normalise(p["text"]) for p in pack["passages"]}
    failures = []
    for claim in draft["claims"]:
        passage = by_id.get(claim["passage"])
        if passage is None:
            continue  # reported by the link check
        if normalise(claim["quote"]) not in passage:
            failures.append(f"claim {claim['id']}: the quote is not in passage {claim['passage']} word for word")
    return failures


def link_check(draft, pack, copyable):
    by_id = {f"P{p['id']}": p for p in pack["passages"]}
    failures = []
    for claim in draft["claims"]:
        passage = by_id.get(claim["passage"])
        if passage is None:
            failures.append(f"claim {claim['id']}: passage {claim['passage']} is not in the evidence pack")
        elif not copyable.get(passage["source"], False):
            failures.append(f"claim {claim['id']}: source {passage['source']} is not an allowed source")
    return failures


def _texts_to_scan(draft):
    for bullet in draft["brief"]:
        yield "brief", bullet
    for part in ("editorial", "deep_dive"):
        for section in draft[part]:
            yield f"{part} '{section['heading']}'", section["text"]
    for point in draft["mains_question"]["approach"]:
        yield "Mains approach", point
    yield "Mains question", draft["mains_question"]["question"]
    for i, q in enumerate(draft["recall_questions"], 1):
        yield f"recall question {i} stem", q["question"]
        yield f"recall question {i} explanation", q["explanation"]


def figure_check(draft):
    allowed = set()
    for claim in draft["claims"]:
        allowed |= numbers_in(claim["text"], words=True) | numbers_in(claim["quote"], words=True)
    failures = []
    for where, text in _texts_to_scan(draft):
        stray = sorted(numbers_in(text) - allowed)
        if stray:
            failures.append(f"{where}: the figure(s) {', '.join(stray)} appear in no claim")
    return failures


def run_code_checks(draft, pack, copyable):
    """Return a list of failure messages. Empty means all three checks pass."""
    return quote_check(draft, pack) + link_check(draft, pack, copyable) + figure_check(draft)
