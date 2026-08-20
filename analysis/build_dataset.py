"""Export a consolidated, flat dataset from every classified book across all three frames.

Supplemental, not authoritative: the per-frame fragment CSVs and classified_*/ directories
(see raw_data/DATASET.md) remain the source of truth build_report.py reads. This script reuses
build_report.load() -- the same join/label logic the live report runs -- and serializes its
result to two presentable CSVs instead of HTML, so the dataset can never drift from the page.

Regenerate with: python3 analysis/build_dataset.py
"""
import csv, os

from build_report import load

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "dataset")

BOOK_FIELDS = [
    "sample_id", "frame", "year", "title", "author",
    "label", "raw_label", "confidence", "narrating_situation", "agent_note", "why",
    "n_quotes", "event_past", "event_present", "beat_past", "beat_present",
    "bucket_event", "bucket_dialogue", "bucket_gnomic", "bucket_paratext", "bucket_unclear",
]

QUOTE_FIELDS = [
    "sample_id", "frame", "year", "title",
    "quote_id", "bucket", "tense", "beat_tense", "note", "quote_text",
]


def book_row(r):
    return {
        "sample_id": r["sid"], "frame": r["frame"], "year": r["year"],
        "title": r["title"], "author": r["author"],
        "label": r["label"], "raw_label": r["raw"], "confidence": r["conf"],
        "narrating_situation": r["sit"], "agent_note": r["note"], "why": r["why"],
        "n_quotes": r["n"],
        "event_past": r["ev"][0], "event_present": r["ev"][1],
        "beat_past": r["bt"][0], "beat_present": r["bt"][1],
        "bucket_event": r["bk"][0], "bucket_dialogue": r["bk"][1],
        "bucket_gnomic": r["bk"][2], "bucket_paratext": r["bk"][3], "bucket_unclear": r["bk"][4],
    }


def quote_rows(r):
    for q in r["q"]:
        yield {
            "sample_id": r["sid"], "frame": r["frame"], "year": r["year"], "title": r["title"],
            "quote_id": q["id"], "bucket": q["b"], "tense": q["t"], "beat_tense": q["bt"],
            "note": q["n"], "quote_text": q["x"],
        }


def main():
    rows, missing, frame_n, skipped = load()
    os.makedirs(OUT, exist_ok=True)

    books_path = os.path.join(OUT, "books.csv")
    with open(books_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=BOOK_FIELDS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(book_row(r))

    nq = 0
    quotes_path = os.path.join(OUT, "quotes.csv")
    with open(quotes_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=QUOTE_FIELDS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            for qr in quote_rows(r):
                w.writerow(qr)
                nq += 1

    print(f"wrote {books_path} ({len(rows)} books)")
    print(f"wrote {quotes_path} ({nq} quotes)"
          + (f", {missing} quotes missing text" if missing else ""))


if __name__ == "__main__":
    main()
