# Past paper tools

Scripts that turn the official question papers into numbered questions, on your own machine. They read UPSC material, so their output stays in `data/raw/`, which Git ignores. See the [reuse policy](../../docs/evals/PAST_PAPERS_POLICY.md).

The official PDFs are scanned images with no text layer, so the first step is OCR. It uses the macOS Vision framework, so it needs a Mac.

| File | What it does |
|---|---|
| `ocr_pdf.py` | Reads a PDF page by page and writes the text. Pages are read in two columns, left then right, which suits the Prelims layout |
| `split_questions.py` | Finds the questions in the text, counts them against what each paper should have, and writes `data/past_papers/completeness.csv` |

## Set up

```
python3 -m venv .venv && .venv/bin/pip install pymupdf ocrmac pillow
```

## Run

1. Download the PDFs listed in `data/past_papers/index.csv` into `data/raw/past_papers/`, named `YEAR_STAGE_PAPER.pdf`.
2. For each PDF, run `ocr_pdf.py <pdf> <text file> [page numbers]`. Prelims pages alternate between Hindi and English, so run the English pages into `data/raw/text_cols/`. Mains papers go into `data/raw/text/`.
3. Run `python3 tools/past_papers/split_questions.py` from the repository root.

## Known limits

- Prelims questions are found by number. 91 to 100 of the 100 are found per paper. The `missing_numbers` column in `completeness.csv` says which ones are not.
- Mains questions carry no printed numbers in the OCR text, so they are split on the marks that follow each question. Counts can be off by a few (two-part case studies split in two, and some marks are misread). Treat Mains counts as approximate.
- OCR makes small errors. Anything that matters should be checked against the official paper.
