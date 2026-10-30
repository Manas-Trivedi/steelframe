"""Split locally OCR'd UPSC papers into questions and count them.

Reads text from data/raw/text (Mains, single column) and data/raw/text_cols
(Prelims, column-aware). Writes question text to data/raw/questions (git-excluded,
because it is UPSC material) and the per-paper question counts to
data/past_papers/completeness.csv (counts only, safe to publish).

The OCR step needs macOS (Vision framework). See tools/past_papers/README.md.
"""
import csv, glob, json, os, re

RAW = "data/raw"
OUT = f"{RAW}/questions"
os.makedirs(OUT, exist_ok=True)

EXPECTED = {"GS-I": 100, "GS1": 20, "GS2": 20, "GS3": 20, "GS4": 20}

ANSWER_LIMIT = re.compile(r"^\(?\s*(answer in|in about|in not more than)?\s*(about )?\d+ words\s*\)?\s*[\d½+=\s.]{0,14}$", re.I)
ONLY_MARKS = re.compile(r"^[\d½+=\s.]{1,14}$")
CODE_LINE = re.compile(r"^[A-Z0-9®Đ\-]{2,}(?:[-/ ]*[A-Z0-9®Đ\-]*)*\s*/\s*\d+$|^[A-Z0-9®Đ\-]{3,}$")
TRAILING_MARKS = re.compile(r"\(?(?:answer in|in about)?\s*\d+ words\s*\)?\s*[\d½+=.]{1,12}$|\s[\d½]+(?:[+=][\d½+=]+)?$", re.I)


def mains_questions(text):
    pages = text.split("\f")
    qs, cur = [], []

    def close():
        nonlocal cur
        q = " ".join(cur).strip()
        if len(q) > 25:
            qs.append(q)
        cur = []

    for page in pages[1:]:  # page 1 is the instruction page
        lines = [l.strip() for l in page.split("\n") if l.strip()]
        # drop the footer: booklet code and page number
        while lines and (CODE_LINE.match(lines[-1]) or re.fullmatch(r"\d{1,2}", lines[-1]) or "P.T.O" in lines[-1] or lines[-1] == "***"):
            lines.pop()
        for l in lines:
            if re.fullmatch(r"[A-Z\-]*[0-9]{2}[A-Z]{2}-\d+", l):  # stray print codes
                continue
            if ANSWER_LIMIT.match(l) or ONLY_MARKS.match(l):
                close()
                continue
            m = TRAILING_MARKS.search(l)
            if m and len(l) - len(m.group(0)) > 10:
                cur.append(l[: m.start()].rstrip())
                close()
                continue
            cur.append(l)
    close()
    return qs


def prelims_questions(text):
    """Find where each numbered question starts, then keep a snippet that follows the number.

    OCR can read the two columns slightly out of order, so questions are located by number,
    not by sequence. Numbers 6 and above are rarely used for statements inside a question, so
    the first occurrence is taken as a question start. For 1 to 5, a start is accepted only
    after the previous question has shown its option (d)."""
    lines = [l.strip() for p in text.split("\f") for l in p.split("\n") if l.strip()]
    lines = [l for l in lines if not re.fullmatch(r"\(\d+-[A-Z]\)|[A-Z0-9\-]{6,}", l)]
    starts, seen_d, last = {}, True, 0
    for i, l in enumerate(lines):
        m = re.match(r"^(\d{1,3})\.(?:\s+.*)?$", l)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 100 and n not in starts and (n >= 6 or (n == last + 1 and seen_d)):
                starts[n] = i
                last, seen_d = n, False
                continue
        if re.match(r"^\(?d\)", l):
            seen_d = True
    out = {}
    for n, i in starts.items():
        chunk = []
        first = re.sub(r"^\d{1,3}\.\s*", "", lines[i])
        if first:
            chunk.append(first)
        j = i + 1
        while j < len(lines) and len(" ".join(chunk)) < 380 and not re.match(r"^\(?a\)", lines[j]):
            chunk.append(lines[j])
            j += 1
        out[n] = " ".join(chunk)[:380]
    return out


rows = []
for f in sorted(glob.glob(f"{RAW}/text/*_Mains_GS*.txt")):
    y, stage, paper = os.path.basename(f)[:-4].split("_")
    qs = mains_questions(open(f).read())
    rows.append((int(y), stage, paper, EXPECTED[paper], len(qs), ""))
    with open(f"{OUT}/{y}_{stage}_{paper}.jsonl", "w") as o:
        for i, q in enumerate(qs, 1):
            o.write(json.dumps({"n": i, "text": q}) + "\n")
for f in sorted(glob.glob(f"{RAW}/text_cols/*_Prelims_GS-I.txt")):
    y, stage, paper = os.path.basename(f)[:-4].split("_")
    qs = prelims_questions(open(f).read())
    missing = [n for n in range(1, 101) if n not in qs]
    rows.append((int(y), stage, paper, EXPECTED[paper], len(qs), " ".join(map(str, missing))))
    with open(f"{OUT}/{y}_{stage}_{paper}.jsonl", "w") as o:
        for n in sorted(qs):
            o.write(json.dumps({"n": n, "text": qs[n]}) + "\n")

with open("data/past_papers/completeness.csv", "w", newline="") as o:
    w = csv.writer(o)
    w.writerow(["year", "stage", "paper", "expected_questions", "found_questions", "status", "missing_numbers"])
    for y, s, p, e, n, miss in sorted(rows):
        w.writerow([y, s, p, e, n, "ok" if e == n else "check", miss])
print(len(rows), "papers;", sum(1 for r in rows if r[3] == r[4]), "match expected")
