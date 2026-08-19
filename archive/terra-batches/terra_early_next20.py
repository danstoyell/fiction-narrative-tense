#!/usr/bin/env python3
"""Stage or promote the next one-per-year early-period Terra tranche."""

from __future__ import annotations

import argparse

import terra_early_batch as batch


batch.SAMPLE = batch.DATA / "sample_topn5_1996_2015_next20.csv"
batch.CLASSIFIED = batch.DATA / "classified_topn5_1996_2015_next20"
batch.RUN_ID = "20260812_terra_early_next20_v2"
batch.RUN = batch.DATA / "terra_runs" / batch.RUN_ID
batch.JOBS = batch.RUN / "jobs"


parser = argparse.ArgumentParser()
parser.add_argument("command", choices=("prepare", "promote"))
arguments = parser.parse_args()
{"prepare": batch.prepare, "promote": batch.promote}[arguments.command]()
