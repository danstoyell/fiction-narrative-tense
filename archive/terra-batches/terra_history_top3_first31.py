#!/usr/bin/env python3
"""Stage or promote a fixed snapshot of the first historical top-three fetches."""

from __future__ import annotations

import argparse
import csv

import terra_early_batch as batch


SOURCE_SAMPLE = batch.DATA / "sample_top3_1931_1995.csv"
SNAPSHOT = batch.DATA / "sample_top3_1931_1995_first31.csv"
SELECTION = batch.DATA / "sample_top3_1931_1995_first31_labelable.csv"
NO_QUOTES = batch.DATA / "unlabelable_no_quotes_top3_1931_1995_first31.csv"
BOOKS = batch.DATA / "books_top3_1931_1995.csv"
QUOTES = batch.DATA / "quotes_top3_1931_1995.csv"
ORIGINAL_TASK_TEXT = batch.task_text


def build_selection() -> None:
    fetched = {row["sample_id"] for row in csv.DictReader(BOOKS.open(encoding="utf-8"))}
    rows = [row for row in csv.DictReader(SOURCE_SAMPLE.open(encoding="utf-8")) if row["sample_id"] in fetched]
    quote_ids = {row["sample_id"] for row in csv.DictReader(QUOTES.open(encoding="utf-8"))}
    for path, selected in ((SNAPSHOT, rows),
                           (SELECTION, [row for row in rows if row["sample_id"] in quote_ids]),
                           (NO_QUOTES, [row for row in rows if row["sample_id"] not in quote_ids])):
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(selected)


def task_text(sample_id: str) -> str:
    return ORIGINAL_TASK_TEXT(sample_id).replace("1996–2015", "1931–1995")


batch.task_text = task_text
batch.SAMPLE = SELECTION
batch.BOOK_SOURCES = (BOOKS,)
batch.QUOTE_SOURCES = (QUOTES,)
batch.CLASSIFIED = batch.DATA / "classified_top3_1931_1995_first31"
batch.RUN_ID = "20260813_terra_history_top3_first31_v1"
batch.RUN = batch.DATA / "terra_runs" / batch.RUN_ID
batch.JOBS = batch.RUN / "jobs"


parser = argparse.ArgumentParser()
parser.add_argument("command", choices=("prepare", "promote"))
arguments = parser.parse_args()
if arguments.command == "prepare":
    build_selection()
batch.prepare() if arguments.command == "prepare" else batch.promote()
