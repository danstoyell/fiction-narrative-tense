#!/usr/bin/env python3
"""Run the production Terra harness against the next pending queue entries."""

from __future__ import annotations

import argparse
import csv
import glob
import json
from collections import Counter
from pathlib import Path

import terra_pilot as pilot


ROOT = Path(__file__).parent
DATA = ROOT / "data"
DEFAULT_RUN_ID = "20260811_terra_prod_batch_50_v2"


def complete_sample_ids() -> set[str]:
    quote_counts = Counter(
        row["sample_id"]
        for row in csv.DictReader((DATA / "quotes_topn.csv").open(encoding="utf-8"))
    )
    complete = set()
    for path in glob.glob(str(DATA / "classified" / "*.json")):
        try:
            record = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sample_id = record.get("sample_id", "")
        if len(record.get("quotes") or []) >= quote_counts.get(sample_id, float("inf")):
            complete.add(sample_id)
    return complete


def next_pending(count: int) -> tuple[str, ...]:
    complete = complete_sample_ids()
    selected = []
    for batch in sorted((DATA / "batches").glob("q*.txt")):
        for sample_id in batch.read_text(encoding="utf-8").splitlines():
            if not sample_id or sample_id in complete or not sample_id.startswith("top20"):
                continue
            destination = DATA / "classified" / f"{pilot.safe_name(sample_id)}.json"
            if destination.exists():
                continue
            selected.append(sample_id)
            if len(selected) == count:
                return tuple(selected)
    raise SystemExit(f"only found {len(selected)} pending eligible books; need {count}")


def configure(run_id: str, sample_ids: tuple[str, ...] | None = None) -> None:
    pilot.RUN_ID = run_id
    pilot.RUN = DATA / "terra_runs" / run_id
    pilot.JOBS = pilot.RUN / "jobs"
    if sample_ids is not None:
        pilot.SAMPLE_IDS = sample_ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "promote"))
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--count", type=int, default=50)
    args = parser.parse_args()
    if args.command == "prepare":
        sample_ids = next_pending(args.count)
        configure(args.run_id, sample_ids)
        pilot.prepare()
        for sample_id in sample_ids:
            print(sample_id)
    else:
        configure(args.run_id)
        pilot.promote()


if __name__ == "__main__":
    main()
