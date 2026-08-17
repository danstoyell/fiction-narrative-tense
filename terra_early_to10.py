#!/usr/bin/env python3
"""Stage or promote classifications needed to reach ten labels per early year."""

from __future__ import annotations

import argparse
import csv

import terra_early_batch as batch


SOURCE_SAMPLE = batch.DATA / "sample_topn5_1996_2015_to10.csv"
SELECTION = batch.DATA / "sample_topn5_1996_2015_to10_labelable.csv"
NO_QUOTES = batch.DATA / "unlabelable_no_quotes_1996_2015_to10.csv"


def build_selection() -> None:
    rows = list(csv.DictReader(SOURCE_SAMPLE.open(encoding="utf-8")))
    quote_ids = {
        row["sample_id"]
        for row in csv.DictReader(
            (batch.DATA / "quotes_topn5_1996_2015_to10.csv").open(encoding="utf-8")
        )
    }
    labelable = [row for row in rows if row["sample_id"] in quote_ids]
    no_quotes = [row for row in rows if row["sample_id"] not in quote_ids]
    if len(labelable) + len(no_quotes) != len(rows):
        raise SystemExit("selection does not account for every fetched book")

    for path, selected in ((SELECTION, labelable), (NO_QUOTES, no_quotes)):
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(selected)
    print(f"prepared {len(labelable)} labelable books and {len(no_quotes)} no-quote books")


batch.SAMPLE = SELECTION
batch.BOOK_SOURCES = (batch.DATA / "books_topn5_1996_2015_to10.csv",)
batch.QUOTE_SOURCES = (batch.DATA / "quotes_topn5_1996_2015_to10.csv",)
batch.CLASSIFIED = batch.DATA / "classified_topn5_1996_2015_to10"
batch.RUN_ID = "20260813_terra_early_to10_v1"
batch.RUN = batch.DATA / "terra_runs" / batch.RUN_ID
batch.JOBS = batch.RUN / "jobs"


parser = argparse.ArgumentParser()
parser.add_argument("command", choices=("prepare", "promote"))
arguments = parser.parse_args()
if arguments.command == "prepare":
    build_selection()
batch.prepare() if arguments.command == "prepare" else batch.promote()
