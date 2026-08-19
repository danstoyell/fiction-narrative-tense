#!/usr/bin/env python3
"""Stage or promote the remaining fetched 1996–2015 books."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import terra_early_batch as batch


SELECTION = batch.DATA / "sample_topn5_1996_2015_rest.csv"
NO_QUOTES = batch.DATA / "unlabelable_no_quotes_1996_2015.csv"
CLASSIFIED_SOURCES = (
    batch.DATA / "classified_topn5_1996_2015",
    batch.DATA / "classified_topn5_1996_2015_next20",
    batch.DATA / "classified_topn5_1996_2015_to5",
)
SAMPLE_SOURCES = (
    batch.DATA / "sample_topn5_1996_2016.csv",
    batch.DATA / "sample_topn5_more_1996_2015.csv",
)


def build_selection() -> None:
    classified = {
        json.loads(path.read_text(encoding="utf-8"))["sample_id"]
        for directory in CLASSIFIED_SOURCES
        for path in directory.glob("*.json")
    }
    candidates = [
        row
        for path in SAMPLE_SOURCES
        for row in csv.DictReader(path.open(encoding="utf-8"))
        if 1996 <= int(row["year"]) <= 2015 and row["sample_id"] not in classified
    ]
    quote_ids = {
        row["sample_id"]
        for path in (
            batch.DATA / "quotes_topn5_1996_2016.csv",
            batch.DATA / "quotes_topn5_more_1996_2015.csv",
        )
        for row in csv.DictReader(path.open(encoding="utf-8"))
    }
    rows = [row for row in candidates if row["sample_id"] in quote_ids]
    no_quotes = [row for row in candidates if row["sample_id"] not in quote_ids]
    by_year = Counter(int(row["year"]) for row in rows)
    if len(rows) != 95 or len(no_quotes) != 5:
        raise SystemExit(f"expected 95 labelable and five no-quote books, found {len(rows)} and {len(no_quotes)}")
    with SELECTION.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    with NO_QUOTES.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=no_quotes[0].keys())
        writer.writeheader()
        writer.writerows(no_quotes)


batch.SAMPLE = SELECTION
batch.BOOK_SOURCES = (
    batch.DATA / "books_topn5_1996_2016.csv",
    batch.DATA / "books_topn5_more_1996_2015.csv",
)
batch.QUOTE_SOURCES = (
    batch.DATA / "quotes_topn5_1996_2016.csv",
    batch.DATA / "quotes_topn5_more_1996_2015.csv",
)
batch.CLASSIFIED = batch.DATA / "classified_topn5_1996_2015_rest"
batch.RUN_ID = "20260812_terra_early_rest_v2"
batch.RUN = batch.DATA / "terra_runs" / batch.RUN_ID
batch.JOBS = batch.RUN / "jobs"


parser = argparse.ArgumentParser()
parser.add_argument("command", choices=("prepare", "promote"))
arguments = parser.parse_args()
if arguments.command == "prepare":
    build_selection()
batch.prepare() if arguments.command == "prepare" else batch.promote()
