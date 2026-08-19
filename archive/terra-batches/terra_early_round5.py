#!/usr/bin/env python3
"""Stage or promote quote-bearing books from the 1996--2015 round-five fetch."""

from __future__ import annotations

import argparse
import csv

import terra_early_batch as batch


SOURCE_SAMPLE = batch.DATA / "sample_topn5_1996_2015_to10_round5.csv"
SELECTION = batch.DATA / "sample_topn5_1996_2015_to10_round5_labelable.csv"
BOOKS = batch.DATA / "books_topn5_1996_2015_to10_round5.csv"
QUOTES = batch.DATA / "quotes_topn5_1996_2015_to10_round5.csv"


def build_selection() -> None:
    quote_bearing = {row["sample_id"] for row in csv.DictReader(QUOTES.open(encoding="utf-8"))}
    rows = [row for row in csv.DictReader(SOURCE_SAMPLE.open(encoding="utf-8"))
            if row["sample_id"] in quote_bearing]
    with SELECTION.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"prepared {len(rows)} quote-bearing round-five jobs")


batch.SAMPLE = SELECTION
batch.BOOK_SOURCES = (BOOKS,)
batch.QUOTE_SOURCES = (QUOTES,)
batch.CLASSIFIED = batch.DATA / "classified_topn5_1996_2015_to10_round5"
batch.RUN_ID = "20260814_terra_early_round5_v1"
batch.RUN = batch.DATA / "terra_runs" / batch.RUN_ID
batch.JOBS = batch.RUN / "jobs"


parser = argparse.ArgumentParser()
parser.add_argument("command", choices=("prepare", "promote"))
arguments = parser.parse_args()
if arguments.command == "prepare":
    build_selection()
batch.prepare() if arguments.command == "prepare" else batch.promote()
