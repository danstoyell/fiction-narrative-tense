#!/usr/bin/env python3
"""Stage or promote newly completed quote-bearing books from the final historical refill."""

from __future__ import annotations

import argparse
import csv
import glob
import json

import terra_early_batch as batch


SOURCE_SAMPLE = batch.DATA / "sample_top3_1931_1995_zero_label_final.csv"
SELECTION = batch.DATA / "sample_top3_1931_1995_zero_label_final_rest_labelable.csv"
BOOKS = batch.DATA / "books_top3_1931_1995_zero_label_final.csv"
QUOTES = batch.DATA / "quotes_top3_1931_1995_zero_label_final.csv"
ORIGINAL_TASK_TEXT = batch.task_text


def build_selection() -> None:
    quote_bearing = {row["sample_id"] for row in csv.DictReader(QUOTES.open(encoding="utf-8"))}
    classified = {
        json.load(open(path, encoding="utf-8"))["sample_id"]
        for path in glob.glob(str(batch.DATA / "classified_top3_1931_1995_zero_label_final*" / "*.json"))
    }
    rows = [row for row in csv.DictReader(SOURCE_SAMPLE.open(encoding="utf-8"))
            if row["sample_id"] in quote_bearing and row["sample_id"] not in classified]
    with SELECTION.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"prepared {len(rows)} remaining completed historical refill jobs")


batch.task_text = lambda sample_id: ORIGINAL_TASK_TEXT(sample_id).replace("1996–2015", "1931–1995")
batch.SAMPLE = SELECTION
batch.BOOK_SOURCES = (BOOKS,)
batch.QUOTE_SOURCES = (QUOTES,)
batch.CLASSIFIED = batch.DATA / "classified_top3_1931_1995_zero_label_final_rest"
batch.RUN_ID = "20260814_terra_history_top3_zero_label_final_rest_v1"
batch.RUN = batch.DATA / "terra_runs" / batch.RUN_ID
batch.JOBS = batch.RUN / "jobs"


parser = argparse.ArgumentParser()
parser.add_argument("command", choices=("prepare", "promote"))
arguments = parser.parse_args()
if arguments.command == "prepare":
    build_selection()
batch.prepare() if arguments.command == "prepare" else batch.promote()
