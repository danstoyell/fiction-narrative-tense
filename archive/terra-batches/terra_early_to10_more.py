#!/usr/bin/env python3
"""Stage or promote the next classifications needed to reach ten early labels."""

from __future__ import annotations

import argparse

import terra_early_batch as batch


batch.SAMPLE = batch.DATA / "sample_topn5_1996_2015_to10_more.csv"
batch.BOOK_SOURCES = (batch.DATA / "books_topn5_1996_2015_to10_more.csv",)
batch.QUOTE_SOURCES = (batch.DATA / "quotes_topn5_1996_2015_to10_more.csv",)
batch.CLASSIFIED = batch.DATA / "classified_topn5_1996_2015_to10_more"
batch.RUN_ID = "20260813_terra_early_to10_more_v1"
batch.RUN = batch.DATA / "terra_runs" / batch.RUN_ID
batch.JOBS = batch.RUN / "jobs"


parser = argparse.ArgumentParser()
parser.add_argument("command", choices=("prepare", "promote"))
arguments = parser.parse_args()
{"prepare": batch.prepare, "promote": batch.promote}[arguments.command]()
