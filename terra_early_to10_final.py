#!/usr/bin/env python3
"""Stage or promote the final targeted early-year classifications."""

from __future__ import annotations

import argparse
import csv

import terra_early_batch as batch


SOURCE_SAMPLE = batch.DATA / "sample_topn5_1996_2015_to10_final.csv"
SELECTION = batch.DATA / "sample_topn5_1996_2015_to10_final_labelable.csv"
NO_QUOTES = batch.DATA / "unlabelable_no_quotes_1996_2015_to10_final.csv"


def build_selection() -> None:
    rows = list(csv.DictReader(SOURCE_SAMPLE.open(encoding="utf-8")))
    quote_ids = {
        row["sample_id"]
        for row in csv.DictReader(
            (batch.DATA / "quotes_topn5_1996_2015_to10_final.csv").open(encoding="utf-8")
        )
    }
    for path, selected in ((SELECTION, [row for row in rows if row["sample_id"] in quote_ids]),
                           (NO_QUOTES, [row for row in rows if row["sample_id"] not in quote_ids])):
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(selected)


batch.SAMPLE = SELECTION
batch.BOOK_SOURCES = (batch.DATA / "books_topn5_1996_2015_to10_final.csv",)
batch.QUOTE_SOURCES = (batch.DATA / "quotes_topn5_1996_2015_to10_final.csv",)
batch.CLASSIFIED = batch.DATA / "classified_topn5_1996_2015_to10_final"
batch.RUN_ID = "20260813_terra_early_to10_final_v1"
batch.RUN = batch.DATA / "terra_runs" / batch.RUN_ID
batch.JOBS = batch.RUN / "jobs"


parser = argparse.ArgumentParser()
parser.add_argument("command", choices=("prepare", "promote"))
arguments = parser.parse_args()
if arguments.command == "prepare":
    build_selection()
batch.prepare() if arguments.command == "prepare" else batch.promote()
