#!/usr/bin/env python3
"""Run blind Terra-medium classification for a historical zero-label refill batch."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import terra_resolution_corrections as batch


ROOT = Path(__file__).parent.parent
DATA = ROOT / "raw_data"


def configure(round_name: str) -> Path:
    batch.SAMPLE = DATA / f"sample_top3_1931_1995_zero_label_{round_name}.csv"
    batch.SOURCE_BOOKS = DATA / f"books_top3_1931_1995_zero_label_{round_name}.csv"
    batch.SOURCE_QUOTES = DATA / f"quotes_top3_1931_1995_zero_label_{round_name}.csv"
    batch.RUN_ID = f"20260820_terra_history_zero_label_{round_name}_v1"
    batch.RUN = DATA / "terra_runs" / batch.RUN_ID
    batch.JOBS = batch.RUN / "jobs"
    return DATA / f"classified_top3_1931_1995_zero_label_{round_name}"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_quote_ids(sample_id: str) -> list[str]:
    books = {
        row["sample_id"]: row
        for row in csv.DictReader(batch.SOURCE_BOOKS.open(encoding="utf-8"))
    }
    work_id = books[sample_id].get("gr_work_id", "")
    seen_text = set()
    quote_ids = []
    for quote in csv.DictReader(batch.SOURCE_QUOTES.open(encoding="utf-8")):
        if quote["sample_id"] != sample_id or quote.get("gr_work_id", "") != work_id:
            continue
        text_key = " ".join(quote["quote_text"].split())
        if not text_key or text_key in seen_text:
            continue
        seen_text.add(text_key)
        quote_ids.append(quote["quote_id"])
    return quote_ids


def restore_source_quote_ids(payload: dict, sample_id: str) -> dict:
    quote_ids = source_quote_ids(sample_id)
    if len(payload["quotes"]) != len(quote_ids):
        raise SystemExit(
            f"{sample_id}: classified/source quote count mismatch "
            f"({len(payload['quotes'])} != {len(quote_ids)})"
        )
    for quote, quote_id in zip(payload["quotes"], quote_ids):
        quote["quote_id"] = quote_id
    return payload


def promote(destination_dir: Path) -> None:
    manifest_path = batch.RUN / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ready = []
    for entry in manifest["books"]:
        state = batch.result_state(entry)
        if state == "no_quotes":
            continue
        if state != "valid":
            raise SystemExit(f"{entry['sample_id']}: result is {state}, not valid")
        source = Path(entry["staged_result"])
        destination = destination_dir / f"{batch.safe_name(entry['sample_id'])}.json"
        if destination.exists():
            raise SystemExit(f"refusing to overwrite {destination}")
        payload = restore_source_quote_ids(
            json.loads(source.read_text(encoding="utf-8")), entry["sample_id"]
        )
        ready.append((entry, payload, destination))

    destination_dir.mkdir(exist_ok=True)
    for entry, payload, destination in ready:
        temporary = destination.with_suffix(".json.terra-tmp")
        temporary.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
        os.replace(temporary, destination)
        entry["status"] = "promoted"
        entry["production_output"] = str(destination)
        entry["output_sha256"] = digest(destination)
        entry["promoted_at"] = datetime.now(UTC).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"promoted {len(ready)} validated classifications -> {destination_dir}")


def sync_quote_ids(destination_dir: Path) -> None:
    manifest_path = batch.RUN / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    changed = 0
    for entry in manifest["books"]:
        destination = destination_dir / f"{batch.safe_name(entry['sample_id'])}.json"
        if not destination.exists():
            continue
        payload = json.loads(destination.read_text(encoding="utf-8"))
        before = [quote["quote_id"] for quote in payload["quotes"]]
        restore_source_quote_ids(payload, entry["sample_id"])
        after = [quote["quote_id"] for quote in payload["quotes"]]
        if before != after:
            temporary = destination.with_suffix(".json.terra-tmp")
            temporary.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
            os.replace(temporary, destination)
            changed += 1
        entry["output_sha256"] = digest(destination)
        entry["source_quote_ids_synced_at"] = datetime.now(UTC).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"synchronized source quote IDs in {changed} classification(s)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("prepare", "run", "status", "promote", "sync-quote-ids")
    )
    parser.add_argument("--round", default="round2")
    args = parser.parse_args()
    destination = configure(args.round)
    if args.command == "prepare":
        batch.prepare()
    elif args.command == "run":
        batch.run_all()
    elif args.command == "status":
        batch.status()
    elif args.command == "sync-quote-ids":
        sync_quote_ids(destination)
    else:
        promote(destination)


if __name__ == "__main__":
    main()
