#!/usr/bin/env python3
"""Refetch known exact Goodreads editions that conservative search could not resolve."""

from __future__ import annotations

import csv
import datetime
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from booktense import goodreads as gr


AUDIT = ROOT / "raw_data" / "resolution_audit_20260819"
SAMPLE = AUDIT / "refetch_sample.csv"
BOOKS = AUDIT / "corrected_books.csv"
QUOTES = AUDIT / "corrected_quotes.csv"
OVERRIDES = {
    "top1961:1919": ("5113", "https://www.goodreads.com/book/show/5113.Franny_and_Zooey"),
    "top2001:710": ("129012", "https://www.goodreads.com/book/show/129012.Black_House"),
    "top2013:163": ("7743175", "https://www.goodreads.com/book/show/7743175-a-memory-of-light"),
    "top2013:3892": ("29429045", "https://www.goodreads.com/book/show/29429045-s"),
    "top2004:2502": ("823762", "https://www.goodreads.com/book/show/823762.Jonathan_Strange_and_Mr_Norrell"),
}


def read(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8")))


def write(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    temporary = path.with_suffix(path.suffix + ".override-tmp")
    with temporary.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fieldnames} for row in rows)
    os.replace(temporary, path)


def main() -> None:
    samples = {row["sample_id"]: row for row in read(SAMPLE)}
    book_rows = read(BOOKS)
    quote_rows = read(QUOTES)
    book_fields = list(book_rows[0])
    quote_fields = list(quote_rows[0])
    now = datetime.datetime.now().isoformat(timespec="seconds")
    provenance = []

    for sample_id, (book_id, source_url) in OVERRIDES.items():
        sample = samples[sample_id]
        print(f"fetching verified edition for {sample['title']}", flush=True)
        page = gr.fetch(source_url, patient=True)
        record = gr._record(page, book_id, "verified_book_id", sample["title"], sample["author"], sample["year"])
        if sample_id == "top2013:3892" and record["confidence"] == "review" and "Doug Dorst" in page:
            title_ok, _, _ = gr.title_match(sample["title"], record["gr_title"])
            if title_ok:
                record["confidence"] = "medium"
                record["notes"] = "verified_secondary_author_doug_dorst"
        record = gr._validate_work_record(record, sample["title"], patient=True)
        if not record["work_id"] or record["confidence"] == "review":
            raise SystemExit(f"verified edition failed validation for {sample_id}: {record}")
        fetched_quotes, raw_count = gr.quotes(
            record["work_id"], 4, patient=True, expected_title=sample["title"]
        )

        book_rows = [row for row in book_rows if row["sample_id"] != sample_id]
        quote_rows = [row for row in quote_rows if row["sample_id"] != sample_id]
        book_rows.append({
            "sample_id": sample_id,
            "stratum": sample["stratum"],
            "title": sample["title"],
            "author": sample["author"],
            "year": sample.get("year", ""),
            "isbn": sample.get("isbn", ""),
            "gr_book_id": record["book_id"],
            "gr_work_id": record["work_id"],
            "gr_title": record["gr_title"],
            "gr_author": record["gr_author"],
            "gr_year": record["gr_year"] or "",
            "gr_ratings": record["ratings"],
            "resolve_method": record["method"],
            "resolve_confidence": record["confidence"],
            "resolve_notes": record["notes"],
            "pages_fetched": max((page_number for page_number, *_ in fetched_quotes), default=0),
            "quotes_raw": raw_count,
            "quotes_dedup": len(fetched_quotes),
            "fetched_at": now,
        })
        for index, (page_number, page_index, quote_url, text) in enumerate(fetched_quotes, 1):
            quote_rows.append({
                "quote_id": f"q{index:05d}",
                "sample_id": sample_id,
                "gr_work_id": record["work_id"],
                "page": page_number,
                "idx": page_index,
                "source_url": quote_url,
                "quote_text": text,
                "bucket": "",
                "tense": "",
                "note": "",
            })
        provenance.append({
            "sample_id": sample_id,
            "title": sample["title"],
            "gr_book_id": book_id,
            "source_url": source_url,
            "title_validation": "book and work quote-page titles passed",
            "quotes_dedup": str(len(fetched_quotes)),
        })
        write(BOOKS, book_fields, book_rows)
        write(QUOTES, quote_fields, quote_rows)
        print(f"  {record['gr_title']} / work {record['work_id']} / {len(fetched_quotes)} quotes")

    write(
        AUDIT / "verified_resolution_overrides.csv",
        ["sample_id", "title", "gr_book_id", "source_url", "title_validation", "quotes_dedup"],
        provenance,
    )


if __name__ == "__main__":
    main()
