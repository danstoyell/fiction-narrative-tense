#!/usr/bin/env python3
"""Atomically integrate validated Goodreads refetches and Terra classifications."""

from __future__ import annotations

import csv
import glob
import hashlib
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path


HERE = Path(__file__).parent
ROOT = HERE.parent
DATA = ROOT / "raw_data"
AUDIT = DATA / "resolution_audit_20260819"
RUN = AUDIT / "20260820_terra_resolution_corrections_v1"
BACKUP = RUN / "integration_backup"
MARKER = RUN / "integration_manifest.json"

sys.path.insert(0, str(HERE))
import build_report


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8")))


def write_csv_atomic(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    temporary = path.with_suffix(path.suffix + ".resolution-tmp")
    with temporary.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fieldnames} for row in rows)
    os.replace(temporary, path)


def backup(path: Path) -> None:
    relative = path.relative_to(ROOT)
    destination = BACKUP / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not destination.exists():
        shutil.copy2(path, destination)


def source_locations(sample_id: str) -> list[tuple[dict, Path, Path]]:
    locations = []
    year = int(sample_id[3:7])
    for source in build_report.SOURCES:
        if not source["lo"] <= year <= source["hi"]:
            continue
        for book_name, quote_name in zip(source["books"], source["quotes"], strict=True):
            book_path = DATA / book_name
            if any(row["sample_id"] == sample_id for row in read_csv(book_path)):
                locations.append((source, book_path, DATA / quote_name))
    return locations


def classification_paths(source: dict, sample_id: str) -> list[Path]:
    paths = []
    for pattern in source["dirs"]:
        for path_string in glob.glob(str(DATA / pattern / "*.json")):
            path = Path(path_string)
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if payload.get("sample_id") == sample_id:
                paths.append(path)
    return sorted(set(paths))


def new_destination(source: dict, sample_id: str) -> Path:
    safe_name = sample_id.translate(str.maketrans({"/": "_", ":": "_", "|": "_", "'": "_"}))
    if source["key"] == "modern":
        directory = DATA / "classified"
    elif source["key"] == "pilot":
        directory = DATA / "classified_top3_1931_1995_resolution_corrections"
    else:
        directory = DATA / "classified_topn5_1996_2015_resolution_corrections"
    directory.mkdir(exist_ok=True)
    return directory / f"{safe_name}.json"


def main() -> None:
    if MARKER.exists():
        raise SystemExit(f"corrections already integrated: {MARKER}")
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    books = {row["sample_id"]: row for row in read_csv(RUN / "corrected_books.csv")}
    quote_rows = read_csv(RUN / "corrected_quotes.csv")
    quotes: dict[str, list[dict[str, str]]] = {sample_id: [] for sample_id in books}
    for row in quote_rows:
        quotes[row["sample_id"]].append(row)

    entries = {entry["sample_id"]: entry for entry in manifest["books"]}
    results = {}
    for sample_id, entry in entries.items():
        if entry["quote_count"]:
            result_path = Path(entry["staged_result"])
            if not result_path.exists():
                raise SystemExit(f"missing Terra result for {sample_id}")
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            expected_ids = [row["quote_id"] for row in quotes[sample_id]]
            build_report.tally(payload["quotes"], "include")
            if payload.get("sample_id") != sample_id or [q.get("quote_id") for q in payload["quotes"]] != expected_ids:
                raise SystemExit(f"invalid or misordered Terra result for {sample_id}")
            results[sample_id] = payload

    changes = []
    BACKUP.mkdir(parents=True)
    for sample_id, book in books.items():
        locations = source_locations(sample_id)
        if not locations:
            raise SystemExit(f"no active source row for {sample_id}")
        touched_classifications = set()
        for source, book_path, quote_path in locations:
            backup(book_path)
            book_rows = read_csv(book_path)
            fieldnames = list(book_rows[0])
            replacements = 0
            for index, row in enumerate(book_rows):
                if row["sample_id"] == sample_id:
                    book_rows[index] = {**row, **{field: book.get(field, "") for field in fieldnames}}
                    replacements += 1
            if replacements != 1:
                raise SystemExit(f"expected one row for {sample_id} in {book_path}, found {replacements}")
            write_csv_atomic(book_path, book_rows, fieldnames)

            backup(quote_path)
            old_quote_rows = read_csv(quote_path)
            quote_fields = list(old_quote_rows[0]) if old_quote_rows else list(quote_rows[0])
            kept = [row for row in old_quote_rows if row["sample_id"] != sample_id]
            kept.extend(quotes[sample_id])
            write_csv_atomic(quote_path, kept, quote_fields)

            active_paths = classification_paths(source, sample_id)
            if results.get(sample_id):
                destinations = active_paths or [new_destination(source, sample_id)]
                for destination in destinations:
                    if destination in touched_classifications:
                        continue
                    backup(destination)
                    temporary = destination.with_suffix(".json.resolution-tmp")
                    temporary.write_text(json.dumps(results[sample_id], indent=1) + "\n", encoding="utf-8")
                    os.replace(temporary, destination)
                    touched_classifications.add(destination)
            else:
                for old_path in active_paths:
                    if old_path in touched_classifications:
                        continue
                    backup(old_path)
                    old_path.unlink()
                    touched_classifications.add(old_path)

        changes.append({
            "sample_id": sample_id,
            "title": book["title"],
            "gr_book_id": book["gr_book_id"],
            "gr_work_id": book["gr_work_id"],
            "gr_title": book["gr_title"],
            "quote_count": len(quotes[sample_id]),
            "classification": "replaced" if sample_id in results else "removed_no_corrected_quotes",
            "source_files": [str(book_path.relative_to(ROOT)) for _, book_path, _ in locations],
            "classification_files": [str(path.relative_to(ROOT)) for path in sorted(touched_classifications)],
        })

    record = {
        "integrated_at": datetime.now(UTC).isoformat(),
        "run_id": manifest["run_id"],
        "model": manifest["model"],
        "reasoning_effort": manifest["reasoning_effort"],
        "backup": str(BACKUP.relative_to(ROOT)),
        "changes": changes,
    }
    MARKER.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"integrated {len(changes)} corrected mappings; backup at {BACKUP}")


if __name__ == "__main__":
    main()
