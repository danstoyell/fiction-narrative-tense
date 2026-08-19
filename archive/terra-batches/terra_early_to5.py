#!/usr/bin/env python3
"""Stage or promote classifications needed to reach five per early year."""

from __future__ import annotations

import argparse

import terra_early_batch as batch


batch.SAMPLE = batch.DATA / "sample_topn5_1996_2015_to5.csv"
batch.BOOK_SOURCES = (
    batch.DATA / "books_topn5_1996_2016.csv",
    batch.DATA / "books_topn5_more_1996_2015.csv",
)
batch.QUOTE_SOURCES = (
    batch.DATA / "quotes_topn5_1996_2016.csv",
    batch.DATA / "quotes_topn5_more_1996_2015.csv",
)
batch.CLASSIFIED = batch.DATA / "classified_topn5_1996_2015_to5"
batch.RUN_ID = "20260812_terra_early_to5_v2"
batch.RUN = batch.DATA / "terra_runs" / batch.RUN_ID
batch.JOBS = batch.RUN / "jobs"


parser = argparse.ArgumentParser()
parser.add_argument("command", choices=("prepare", "promote"))
arguments = parser.parse_args()
{"prepare": batch.prepare, "promote": batch.promote}[arguments.command]()
